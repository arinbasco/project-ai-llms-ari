"""Pruebas del redactor con un modelo falso, sin gastar llamadas a Groq."""

import sys
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.clientes import Cliente, Voz
from redaccion.prompts import SISTEMA
from redaccion.redactor import (
    CORRIGIENDO,
    REDACTANDO,
    REVISANDO,
    REVISANDO_CORRECCION,
    Pedido,
    armar_ficha,
    armar_mensajes,
    redactar,
    separar,
)

CON_NOTAS = "Texto del post\n\n---\n**NOTAS PARA REVISAR**\nDATOS QUE FALTAN: ninguno"
SIN_NOTAS = "Texto del post sin notas"
RESPUESTA_COMPLETA = ("Café recién tostado.\n\nNOTAS PARA REVISAR\n"
                      "DATOS QUE FALTAN: ninguno\nA VERIFICAR: ninguna\nENFOQUE: directo.")
RESPUESTA_CORREGIDA = ("Café recién tostado. #café\n\nNOTAS PARA REVISAR\n"  # NUEVO
                       "DATOS QUE FALTAN: ninguno\nA VERIFICAR: ninguna\nENFOQUE: añadí un hashtag.")


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


class RedactorQueFallaAlCorregir:  # NUEVO
    """Redactor falso que escribe bien la primera vez y falla al corregir."""

    def __init__(self):
        self.llamadas = 0

    def invoke(self, mensajes):
        self.llamadas += 1
        if self.llamadas > 1:
            raise RuntimeError("sin cuota")
        return AIMessage(content=RESPUESTA_COMPLETA)


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
    resultado = redactar(pedido_valido(), llm, revisor=revisor, reescribir=False)  # NUEVO reescribir
    reglas = {problema.regla for problema in resultado.problemas}
    assert "hashtags" in reglas
    assert "ADORNO" in reglas


def test_redactar_avisa_si_falla_la_capa2():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA])
    resultado = redactar(pedido_valido(), llm, revisor=RevisorRoto(), reescribir=False)  # NUEVO reescribir
    assert resultado.texto == "Café recién tostado."
    assert any("capa 2" in aviso for aviso in resultado.avisos)


def test_tokens_del_revisor_van_aparte():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA])
    resultado = redactar(pedido_valido(), llm, revisor=RevisorConTokens(), reescribir=False)  # NUEVO reescribir
    assert resultado.tokens_revisor_entrada == 100
    assert resultado.tokens_revisor_salida == 20
    assert resultado.tokens_entrada == 0


def test_reescribe_si_hay_problemas():  # NUEVO
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA, RESPUESTA_CORREGIDA])
    revisor = FakeListChatModel(responses=["NINGUNO", "NINGUNO"])
    resultado = redactar(pedido_valido(), llm, revisor=revisor)
    assert resultado.texto == "Café recién tostado."
    assert resultado.correccion.texto == "Café recién tostado. #café"
    assert resultado.correccion.problemas == []


def test_no_reescribe_si_no_hay_problemas():  # NUEVO
    llm = FakeListChatModel(responses=[RESPUESTA_CORREGIDA])
    revisor = FakeListChatModel(responses=["NINGUNO"])
    resultado = redactar(pedido_valido(), llm, revisor=revisor)
    assert resultado.correccion is None


def test_no_reescribe_por_adorno():  # NUEVO
    llm = FakeListChatModel(responses=[RESPUESTA_CORREGIDA])
    revisor = FakeListChatModel(responses=["FRASE: recién tostado\nTIPO: ADORNO\nMOTIVO: x"])
    resultado = redactar(pedido_valido(), llm, revisor=revisor)
    assert resultado.correccion is None


def test_si_falla_la_reescritura_queda_el_original():  # NUEVO
    revisor = FakeListChatModel(responses=["NINGUNO"])
    resultado = redactar(pedido_valido(), RedactorQueFallaAlCorregir(), revisor=revisor)
    assert resultado.texto == "Café recién tostado."
    assert resultado.correccion is None
    assert any("reescritura" in aviso for aviso in resultado.avisos)



def redactar_anotando_etapas(llm, revisor, **opciones):
    """Redacta y devuelve el resultado y las etapas anunciadas, en orden."""
    etapas = []
    resultado = redactar(pedido_valido(), llm, revisor=revisor,
                         avisar=etapas.append, **opciones)
    return resultado, etapas


def test_avisa_las_cuatro_etapas_si_reescribe():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA, RESPUESTA_CORREGIDA])
    revisor = FakeListChatModel(responses=["NINGUNO", "NINGUNO"])
    _, etapas = redactar_anotando_etapas(llm, revisor)
    assert etapas == [REDACTANDO, REVISANDO, CORRIGIENDO, REVISANDO_CORRECCION]


def test_sin_problemas_no_avisa_la_correccion():
    llm = FakeListChatModel(responses=[RESPUESTA_CORREGIDA])
    revisor = FakeListChatModel(responses=["NINGUNO"])
    _, etapas = redactar_anotando_etapas(llm, revisor)
    assert etapas == [REDACTANDO, REVISANDO]


def test_si_falla_la_reescritura_no_avisa_la_segunda_revision():
    revisor = FakeListChatModel(responses=["NINGUNO"])
    _, etapas = redactar_anotando_etapas(RedactorQueFallaAlCorregir(), revisor)
    assert etapas == [REDACTANDO, REVISANDO, CORRIGIENDO]


def test_sin_verificar_solo_avisa_la_redaccion():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA])
    _, etapas = redactar_anotando_etapas(llm, None, verificar_texto=False)
    assert etapas == [REDACTANDO]


def test_sin_avisar_el_resultado_no_cambia():
    llm = FakeListChatModel(responses=[RESPUESTA_COMPLETA, RESPUESTA_CORREGIDA])
    revisor = FakeListChatModel(responses=["NINGUNO", "NINGUNO"])
    resultado = redactar(pedido_valido(), llm, revisor=revisor)
    assert resultado.correccion.texto == "Café recién tostado. #café"
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