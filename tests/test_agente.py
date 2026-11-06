"""Pruebas automáticas. No necesitan clave de API ni internet.

Correr con:  python -m pytest
"""
import json
from types import SimpleNamespace

import pytest

from agente import herramientas as h
from agente.agente import Agente
from agente.db import conectar


@pytest.fixture
def con(tmp_path):
    return conectar(tmp_path / "prueba.db")


def id_de(con, texto):
    return h.buscar_productos(con, texto)[0]["id"]


def test_buscar(con):
    assert [p["nombre"] for p in h.buscar_productos(con, "arroz")] == ["Arroz Tío Pelón 1 kg"]
    assert len(h.buscar_productos(con, categoria="bebidas")) == 2


def test_crear_pedido_descuenta_stock(con):
    arroz = id_de(con, "arroz")
    pedido = h.crear_pedido(con, "Ana", [{"producto_id": arroz, "cantidad": 3}])
    assert pedido["total"] == 3 * 1150
    assert h.buscar_productos(con, "arroz")[0]["stock"] == 37


def test_no_vende_sin_stock(con):
    papel = id_de(con, "papel")
    assert "error" in h.crear_pedido(con, "Ana", [{"producto_id": papel, "cantidad": 1}])


def test_cancelar_devuelve_stock(con):
    cafe = id_de(con, "café")
    pedido = h.crear_pedido(con, "Luis", [{"producto_id": cafe, "cantidad": 5}])
    h.cancelar_pedido(con, pedido["id"])
    assert h.buscar_productos(con, "café")[0]["stock"] == 15
    assert h.reporte_ventas(con)["total_vendido"] == 0


def test_error_no_rompe_el_agente(con):
    salida = json.loads(h.ejecutar(con, "ver_pedido", {"pedido_id": "abc", "extra": 1}))
    assert "error" in salida


class APIFalsa:
    """Imita al modelo: primero pide una herramienta, luego contesta con texto."""

    def __init__(self):
        self.messages = self
        self.llamadas = 0

    def create(self, **kwargs):
        self.llamadas += 1
        if self.llamadas == 1:
            bloque = SimpleNamespace(type="tool_use", id="t1", name="buscar_productos", input={"texto": "leche"})
            return SimpleNamespace(stop_reason="tool_use", content=[bloque])
        resultado = kwargs["messages"][-1]["content"][0]
        assert resultado["type"] == "tool_result" and "Leche" in resultado["content"]
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="La leche cuesta ₡950.")])


def test_ciclo_del_agente(con):
    agente = Agente(con, cliente_api=APIFalsa())
    assert agente.responder("¿Cuánto cuesta la leche?") == "La leche cuesta ₡950."
