"""Herramientas del agente.

Una "herramienta" es una función normal de Python. El modelo de IA no la
ejecuta él mismo: solo pide "quiero usar buscar_productos con estos datos",
nuestro programa la ejecuta y le devuelve el resultado.

Cada herramienta tiene dos partes:
  1. La función en Python (lo que de verdad hace el trabajo).
  2. Su descripción en HERRAMIENTAS (lo que el modelo lee para saber
     cuándo y cómo usarla).
"""
import json
import sqlite3


# ---------------------------------------------------------------- funciones

def buscar_productos(con: sqlite3.Connection, texto: str = "", categoria: str = "") -> list[dict]:
    filas = con.execute(
        """SELECT id, nombre, categoria, precio, stock FROM productos
           WHERE nombre LIKE ? AND categoria LIKE ? ORDER BY nombre""",
        (f"%{texto}%", f"%{categoria}%"),
    ).fetchall()
    return [dict(f) for f in filas]


def crear_pedido(con: sqlite3.Connection, cliente: str, productos: list[dict], telefono: str = "") -> dict:
    """productos = [{"producto_id": 1, "cantidad": 2}, ...]"""
    if not productos:
        return {"error": "El pedido no tiene productos."}

    lineas, total = [], 0
    for item in productos:
        fila = con.execute(
            "SELECT id, nombre, precio, stock FROM productos WHERE id = ?",
            (item["producto_id"],),
        ).fetchone()
        cantidad = int(item["cantidad"])
        if fila is None:
            return {"error": f"No existe un producto con id {item['producto_id']}."}
        if cantidad <= 0:
            return {"error": f"Cantidad inválida para {fila['nombre']}."}
        if fila["stock"] < cantidad:
            return {"error": f"Solo hay {fila['stock']} unidades de {fila['nombre']}."}
        lineas.append((fila, cantidad))
        total += fila["precio"] * cantidad

    # Todo o nada: si algo falla a medio camino, no queda un pedido a medias.
    with con:
        cur = con.execute(
            "INSERT INTO pedidos (cliente, telefono, total) VALUES (?, ?, ?)",
            (cliente, telefono, total),
        )
        pedido_id = cur.lastrowid
        for fila, cantidad in lineas:
            con.execute(
                "INSERT INTO detalle_pedido VALUES (?, ?, ?, ?)",
                (pedido_id, fila["id"], cantidad, fila["precio"]),
            )
            con.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, fila["id"]))

    return ver_pedido(con, pedido_id)


def ver_pedido(con: sqlite3.Connection, pedido_id: int) -> dict:
    pedido = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if pedido is None:
        return {"error": f"No existe el pedido #{pedido_id}."}
    detalle = con.execute(
        """SELECT p.nombre, d.cantidad, d.precio, d.cantidad * d.precio AS subtotal
           FROM detalle_pedido d JOIN productos p ON p.id = d.producto_id
           WHERE d.pedido_id = ?""",
        (pedido_id,),
    ).fetchall()
    return {**dict(pedido), "productos": [dict(d) for d in detalle]}


def cancelar_pedido(con: sqlite3.Connection, pedido_id: int) -> dict:
    pedido = con.execute("SELECT estado FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if pedido is None:
        return {"error": f"No existe el pedido #{pedido_id}."}
    if pedido["estado"] != "pendiente":
        return {"error": f"El pedido #{pedido_id} ya está '{pedido['estado']}', no se puede cancelar."}
    with con:
        # Se devuelve el stock a la tienda.
        con.execute(
            """UPDATE productos SET stock = stock + (
                   SELECT cantidad FROM detalle_pedido
                   WHERE pedido_id = ? AND producto_id = productos.id)
               WHERE id IN (SELECT producto_id FROM detalle_pedido WHERE pedido_id = ?)""",
            (pedido_id, pedido_id),
        )
        con.execute("UPDATE pedidos SET estado = 'cancelado' WHERE id = ?", (pedido_id,))
    return ver_pedido(con, pedido_id)


def reporte_ventas(con: sqlite3.Connection) -> dict:
    resumen = con.execute(
        "SELECT COUNT(*) AS pedidos, COALESCE(SUM(total), 0) AS total FROM pedidos WHERE estado != 'cancelado'"
    ).fetchone()
    mas_vendidos = con.execute(
        """SELECT p.nombre, SUM(d.cantidad) AS unidades
           FROM detalle_pedido d JOIN pedidos pe ON pe.id = d.pedido_id
           JOIN productos p ON p.id = d.producto_id
           WHERE pe.estado != 'cancelado'
           GROUP BY p.id ORDER BY unidades DESC LIMIT 5"""
    ).fetchall()
    poco_stock = con.execute(
        "SELECT nombre, stock FROM productos WHERE stock <= 5 ORDER BY stock"
    ).fetchall()
    return {
        "pedidos": resumen["pedidos"],
        "total_vendido": resumen["total"],
        "mas_vendidos": [dict(f) for f in mas_vendidos],
        "productos_por_agotarse": [dict(f) for f in poco_stock],
    }


# ------------------------------------------- descripciones para el modelo
# Formato "JSON Schema": le dice al modelo qué datos pide cada herramienta.

HERRAMIENTAS = [
    {
        "name": "buscar_productos",
        "description": "Busca productos de la tienda por nombre y/o categoría. Devuelve id, precio (colones) y stock. "
                       "Úsala antes de crear un pedido para conocer el id del producto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "texto": {"type": "string", "description": "Parte del nombre, ej. 'arroz'. Vacío = todos."},
                "categoria": {"type": "string", "description": "granos, bebidas, lácteos, panadería, abarrotes o limpieza."},
            },
        },
    },
    {
        "name": "crear_pedido",
        "description": "Registra un pedido y descuenta el stock. Solo úsala cuando el cliente confirmó qué quiere y dio su nombre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cliente": {"type": "string"},
                "telefono": {"type": "string"},
                "productos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "producto_id": {"type": "integer"},
                            "cantidad": {"type": "integer"},
                        },
                        "required": ["producto_id", "cantidad"],
                    },
                },
            },
            "required": ["cliente", "productos"],
        },
    },
    {
        "name": "ver_pedido",
        "description": "Muestra el estado y detalle de un pedido por su número.",
        "input_schema": {
            "type": "object",
            "properties": {"pedido_id": {"type": "integer"}},
            "required": ["pedido_id"],
        },
    },
    {
        "name": "cancelar_pedido",
        "description": "Cancela un pedido pendiente y devuelve los productos al inventario.",
        "input_schema": {
            "type": "object",
            "properties": {"pedido_id": {"type": "integer"}},
            "required": ["pedido_id"],
        },
    },
    {
        "name": "reporte_ventas",
        "description": "Resumen para el dueño: total vendido, productos más vendidos y productos por agotarse.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

FUNCIONES = {
    "buscar_productos": buscar_productos,
    "crear_pedido": crear_pedido,
    "ver_pedido": ver_pedido,
    "cancelar_pedido": cancelar_pedido,
    "reporte_ventas": reporte_ventas,
}


def ejecutar(con: sqlite3.Connection, nombre: str, datos: dict) -> str:
    """Ejecuta la herramienta que pidió el modelo y devuelve el resultado como texto JSON."""
    funcion = FUNCIONES.get(nombre)
    if funcion is None:
        return json.dumps({"error": f"Herramienta desconocida: {nombre}"})
    try:
        resultado = funcion(con, **datos)
    except Exception as e:  # el modelo recibe el error y puede corregirse
        resultado = {"error": f"{type(e).__name__}: {e}"}
    return json.dumps(resultado, ensure_ascii=False)
