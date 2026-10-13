"""Pruebas del redactor con un modelo falso, sin gastar llamadas a Groq."""

import sys
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.clientes import Cliente, Voz
from redaccion.prompts import SISTEMA
from redaccion.redactor import Pedido, armar_ficha, armar_mensajes, redactar, separar

CON_NOTAS = "Texto del post\n\n---\n**NOTAS PARA REVISAR**\nDATOS QUE FALTAN: ninguno"
SIN_NOTAS = "Texto del post sin notas"
RESPUESTA_COMPLETA = ("Café recién tostado.\n\nNOTAS PARA REVISAR\n"
                      "DATOS QUE FALTAN: ninguno\nA VERIFICAR: ninguna\nENFOQUE: directo.")


class RevisorRoto:
    """Revisor falso que siempre falla, como si Groq no respondiera."""

    def invoke(self, mensajes):
        raise RuntimeError("sin cuota")

class RevisorConTokens:
    """Revisor falso que responde NINGUNO e informa de los tokens gastados."""

    def invoke(self, mensajes):
        return AIMessage(
            content="NINGUNO",
            usage_metadata={"input_tokens": 100, "output_tokens": 20,
                            "total_tokens": 120},
        )


def pedido_valido(**cambios):
    datos = {"tema": "café de Colombia", "plataforma": "X",
             "audiencia": "Infantil", "objetivo": "Vender",
             "cliente": "tostadero-ventura"}
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


def test_la_ficha_entra_en_el_pedido():
    usuario = armar_mensajes(pedido_valido(cliente="banco-faro"))[1].content
    assert usuario.startswith("FICHA DEL CLIENTE")
    assert "Nombre: Banco Faro" in usuario
    assert "Trato: usted y ustedes" in usuario


def test_ficha_con_campos_vacios_escribe_ninguna():
    voz = Voz(tono=[], trato="tu", expresiones_propias=[],
              expresiones_vetadas=[], emojis="")
    cliente = Cliente(id="prueba", nombre="Prueba", tipo="", sector="",
                      descripcion="", voz=voz, limites=[])
    ficha = armar_ficha(cliente)
    assert "Expresiones propias: ninguna" in ficha
    assert "Expresiones que no se usan nunca: ninguna" in ficha
    assert "Tipo: sin indicar" in ficha
    assert "Emojis: sin indicar" in ficha
    assert "LÍMITES\n- ninguno" in ficha


def test_sistema_no_tiene_codigo_suelto():
    assert " = {" not in SISTEMA
    assert " = (" not in SISTEMA


def test_redactar_con_notas_hace_un_solo_intento():
    llm = FakeListChatModel(responses=[CON_NOTAS])
    resultado = redactar(pedido_valido(), llm, verificar_texto=False)
    assert resultado.intentos == 1
    assert resultado.avisos == []


def test_redactar_reintenta_si_faltan_notas():
    llm = FakeListChatModel(responses=[SIN_NOTAS, CON_NOTAS])
    resultado = redactar(pedido_valido(), llm, verificar_texto=False)
    assert resultado.intentos == 2
    assert resultado.notas is not None


def test_redactar_avisa_si_las_notas_faltan_dos_veces():
    llm = FakeListChatModel(responses=[SIN_NOTAS, SIN_NOTAS])
    resultado = redactar(pedido_valido(), llm, verificar_texto=False)
    assert resultado.intentos == 2
    assert len(resultado.avisos) == 1


def test_redactar_junta_capa1_y_capa2():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA])
    revisor = FakeListChatModel(responses=["FRASE: recién tostado\nTIPO: ADORNO\nMOTIVO: x"])
    resultado = redactar(pedido_valido(), llm, revisor=revisor)
    reglas = {problema.regla for problema in resultado.problemas}
    assert "hashtags" in reglas
    assert "ADORNO" in reglas


def test_redactar_avisa_si_falla_la_capa2():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA])
    resultado = redactar(pedido_valido(), llm, revisor=RevisorRoto())
    assert resultado.texto == "Café recién tostado."
    assert any("capa 2" in aviso for aviso in resultado.avisos)

def test_tokens_del_revisor_van_aparte():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA])
    resultado = redactar(pedido_valido(), llm, revisor=RevisorConTokens())
    assert resultado.tokens_revisor_entrada == 100
    assert resultado.tokens_revisor_salida == 20
    assert resultado.tokens_entrada == 0


@pytest.mark.parametrize("cambios", [
    {"tema": "   "},
    {"plataforma": "TikTok"},
    {"audiencia": "Jubilados"},
    {"objetivo": "Entretener"},
    {"cliente": "no-existe"},
])
def test_pedidos_invalidos(cambios):
    with pytest.raises(ValueError):
        pedido_valido(**cambios).validar()