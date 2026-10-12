"""Pruebas del redactor con un modelo falso, sin gastar llamadas a Groq."""

import sys
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.redactor import Pedido, armar_mensajes, redactar, separar

CON_NOTAS = "Texto del post\n\n---\n**NOTAS PARA REVISAR**\nDATOS QUE FALTAN: ninguno"
SIN_NOTAS = "Texto del post sin notas"


def pedido_valido(**cambios):
    datos = {"tema": "café de Colombia", "plataforma": "X",
             "audiencia": "Infantil", "objetivo": "Vender",
             "cliente": "tostadero-ventura"}  # NUEVO
    datos.update(cambios)
    return Pedido(**datos)


def test_separar_texto_y_notas():
    texto, notas = separar(CON_NOTAS)
    assert texto == "Texto del post"
    assert notas.startswith("DATOS QUE FALTAN")


def test_separar_sin_notas_devuelve_none():
    texto, notas = separar(SIN_NOTAS)
    assert texto == SIN_NOTAS
    assert notas is None


def test_ajuste_infantil_y_buscadores_entran_en_el_pedido():
    usuario = armar_mensajes(pedido_valido(buscadores=True))[1].content
    assert "café de Colombia" in usuario
    assert "AJUSTE: INFANTIL Y VENDER" in usuario
    assert "OPTIMIZACIÓN PARA BUSCADORES" in usuario


def test_redactar_con_notas_hace_un_solo_intento():
    llm = FakeListChatModel(responses=[CON_NOTAS])
    resultado = redactar(pedido_valido(), llm)
    assert resultado.intentos == 1
    assert resultado.avisos == []


def test_redactar_reintenta_si_faltan_notas():
    llm = FakeListChatModel(responses=[SIN_NOTAS, CON_NOTAS])
    resultado = redactar(pedido_valido(), llm)
    assert resultado.intentos == 2
    assert resultado.notas is not None


def test_redactar_avisa_si_las_notas_faltan_dos_veces():
    llm = FakeListChatModel(responses=[SIN_NOTAS, SIN_NOTAS])
    resultado = redactar(pedido_valido(), llm)
    assert resultado.intentos == 2
    assert len(resultado.avisos) == 1


@pytest.mark.parametrize("cambios", [
    {"tema": "   "},
    {"plataforma": "TikTok"},
    {"audiencia": "Jubilados"},
    {"objetivo": "Entretener"},
    {"cliente": "no-existe"},  # NUEVO
])
def test_pedidos_invalidos(cambios):
    with pytest.raises(ValueError):
        pedido_valido(**cambios).validar()