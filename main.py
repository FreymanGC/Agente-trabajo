"""Chat en la terminal con el agente de la tienda.

Uso:  python main.py
      python main.py --pasos   (muestra qué herramientas usa el agente)
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()  # carga ANTHROPIC_API_KEY desde el archivo .env

from agente.agente import Agente  # noqa: E402
from agente.db import conectar  # noqa: E402


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Falta la clave de API. Copia .env.example a .env y pon tu ANTHROPIC_API_KEY.")
        sys.exit(1)

    agente = Agente(conectar(), mostrar_pasos="--pasos" in sys.argv)
    print("Minisúper La Esquina — escribe 'salir' para terminar.\n")
    while True:
        try:
            mensaje = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if mensaje.lower() in {"salir", "exit"}:
            break
        if mensaje:
            print(f"Agente: {agente.responder(mensaje)}\n")


if __name__ == "__main__":
    main()
