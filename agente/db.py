"""Base de datos de la tienda (SQLite).

SQLite guarda todo en un solo archivo (tienda.db). No hay que instalar
ningún servidor: viene incluido en Python.
"""
import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).resolve().parent.parent / "tienda.db"

PRODUCTOS_INICIALES = [
    # (nombre, categoria, precio en colones, stock)
    ("Arroz Tío Pelón 1 kg", "granos", 1150, 40),
    ("Frijoles negros 900 g", "granos", 1350, 25),
    ("Café molido 500 g", "bebidas", 3200, 15),
    ("Leche entera 1 L", "lácteos", 950, 30),
    ("Huevos (cartón de 15)", "lácteos", 2600, 12),
    ("Pan cuadrado", "panadería", 1500, 10),
    ("Aceite vegetal 1 L", "abarrotes", 2100, 18),
    ("Azúcar 2 kg", "abarrotes", 1900, 20),
    ("Coca-Cola 2.5 L", "bebidas", 1800, 24),
    ("Jabón de baño", "limpieza", 650, 35),
    ("Papel higiénico (4 rollos)", "limpieza", 1700, 0),
]


def conectar(ruta: Path | str = RUTA_DB) -> sqlite3.Connection:
    """Abre la base de datos y crea las tablas si no existen."""
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row  # permite leer columnas por nombre
    con.execute("PRAGMA foreign_keys = ON")
    crear_tablas(con)
    return con


def crear_tablas(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre    TEXT NOT NULL UNIQUE,
            categoria TEXT NOT NULL,
            precio    INTEGER NOT NULL,
            stock     INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pedidos (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente  TEXT NOT NULL,
            telefono TEXT,
            fecha    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            estado   TEXT NOT NULL DEFAULT 'pendiente',
            total    INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS detalle_pedido (
            pedido_id   INTEGER NOT NULL REFERENCES pedidos(id),
            producto_id INTEGER NOT NULL REFERENCES productos(id),
            cantidad    INTEGER NOT NULL,
            precio      INTEGER NOT NULL
        );
        """
    )
    # Si la tienda está vacía, se llena con productos de ejemplo.
    if con.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO productos (nombre, categoria, precio, stock) VALUES (?, ?, ?, ?)",
            PRODUCTOS_INICIALES,
        )
        con.commit()
