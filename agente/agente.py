"""El corazón del agente: el "ciclo del agente".

1. Mandamos al modelo la conversación + la lista de herramientas.
2. El modelo responde. Puede:
     a) contestar con texto  -> se lo mostramos al cliente y terminamos el turno.
     b) pedir usar una herramienta -> la ejecutamos, le mandamos el resultado
        y volvemos al paso 1.
3. Repetimos hasta que el modelo conteste con texto.
"""
import os
import sqlite3

import anthropic

from . import herramientas

INSTRUCCIONES = """Eres el asistente de "Minisúper La Esquina", una tienda de barrio en la Zona Sur de Costa Rica.
Atiendes por chat a clientes y al dueño.

Reglas:
- Habla en español, amable y breve. Los precios son en colones (₡).
- Nunca inventes productos, precios ni stock: consulta siempre con las herramientas.
- Antes de crear un pedido, resume lo que el cliente va a llevar con el total y pide confirmación y su nombre.
- Si un producto no tiene stock, dilo y ofrece una alternativa parecida.
- Si piden el reporte de ventas, preséntalo ordenado y menciona lo que hay que reabastecer.
"""

MODELO = os.getenv("MODELO", "claude-haiku-5-5")
MAX_PASOS = 10  # freno de seguridad para que el ciclo no sea infinito


class Agente:
    def __init__(self, con: sqlite3.Connection, cliente_api: anthropic.Anthropic | None = None, mostrar_pasos: bool = False):
        self.con = con
        self.api = cliente_api or anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno
        self.historial: list[dict] = []  # la "memoria" de la conversación
        self.mostrar_pasos = mostrar_pasos

    def responder(self, mensaje: str) -> str:
        self.historial.append({"role": "user", "content": mensaje})

        for _ in range(MAX_PASOS):
            respuesta = self.api.messages.create(
                model=MODELO,
                max_tokens=1024,
                system=INSTRUCCIONES,
                tools=herramientas.HERRAMIENTAS,
                messages=self.historial,
            )
            self.historial.append({"role": "assistant", "content": respuesta.content})

            if respuesta.stop_reason != "tool_use":
                # El modelo terminó: juntamos su texto y lo devolvemos.
                return "".join(b.text for b in respuesta.content if b.type == "text")

            # El modelo pidió una o más herramientas: las ejecutamos.
            resultados = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    salida = herramientas.ejecutar(self.con, bloque.name, bloque.input)
                    if self.mostrar_pasos:
                        print(f"   [herramienta] {bloque.name}({bloque.input}) -> {salida[:120]}")
                    resultados.append({"type": "tool_result", "tool_use_id": bloque.id, "content": salida})
            self.historial.append({"role": "user", "content": resultados})

        return "Lo siento, no pude completar la solicitud. ¿Puedes intentarlo de otra forma?"
