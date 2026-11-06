# Agente de trabajo — Minisúper La Esquina

Un agente de IA que atiende clientes de una tienda de barrio: responde precios, revisa inventario,
toma pedidos, los cancela y le da al dueño un reporte de ventas. Proyecto de práctica.

## ¿Qué es un "agente"?

Un chatbot normal solo **habla**. Un agente además **actúa**: tiene herramientas (funciones de
código) que puede decidir usar para conseguir información o hacer cambios reales.

```
 Cliente: "¿Tienen café? Quiero 2"
    │
    ▼
 ┌────────────┐  "quiero usar buscar_productos('café')"   ┌───────────────┐
 │ Modelo IA  │ ────────────────────────────────────────▶ │ Nuestro código │──▶ base de datos
 │  (Claude)  │ ◀──────────────────────────────────────── │ (herramientas) │
 └────────────┘  "Café molido 500 g, ₡3200, stock 15"     └───────────────┘
    │
    ▼
 Agente: "Sí, el café de 500 g cuesta ₡3200. 2 serían ₡6400. ¿A nombre de quién?"
```

Ese ir y venir se llama **ciclo del agente** y está en `agente/agente.py` (unas 30 líneas).

## Estructura

| Archivo | Qué hace |
|---|---|
| `agente/db.py` | Crea la base de datos SQLite (`tienda.db`) con productos de ejemplo |
| `agente/herramientas.py` | Las 5 herramientas y sus descripciones para el modelo |
| `agente/agente.py` | El ciclo del agente y sus instrucciones (personalidad y reglas) |
| `main.py` | Chat en la terminal |
| `tests/` | Pruebas automáticas (no necesitan internet ni clave) |

## Cómo correrlo

1. Instala [Python 3.11+](https://www.python.org/downloads/).
2. En una terminal, dentro de la carpeta del proyecto:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows  (en Mac/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
3. Consigue una clave de API en <https://console.anthropic.com> (requiere poner saldo; con
   pocos dólares alcanza para mucha práctica usando el modelo Haiku).
4. Copia `.env.example` como `.env` y pega tu clave.
5. Corre:
   ```bash
   python main.py --pasos
   ```
   `--pasos` muestra en pantalla cada herramienta que usa el agente — ideal para aprender.

Para correr las pruebas: `python -m pytest`

## Cosas para probar en el chat

- "¿Qué bebidas tienen?"
- "Quiero 2 arroces y una leche" → luego da tu nombre y confirma
- "¿Hay papel higiénico?" (está agotado: mira cómo ofrece alternativa)
- "Cancela el pedido 1"
- "Soy el dueño, dame el reporte de ventas"

## Ideas para seguir practicando

1. Agregar una herramienta `reabastecer(producto_id, cantidad)` para el dueño.
2. Agregar horarios y entregas a domicilio.
3. Conectarlo a WhatsApp o Telegram en vez de la terminal.
4. Hacer una interfaz web.
