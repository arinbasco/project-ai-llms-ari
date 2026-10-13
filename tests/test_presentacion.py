"""Pruebas de las funciones que preparan el resultado para la interfaz."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.presentacion import (
    CLASE_FUERTE,
    CLASE_SUAVE,
    etiqueta,
    ordenar_problemas,
    resaltar,
    separar_notas,
)
from redaccion.verificador import Problema

# --- separar_notas ---


def test_separa_los_tres_apartados():
    notas = ("DATOS QUE FALTAN: el precio\nA VERIFICAR: la fecha\n"
             "y el lugar\nENFOQUE: directo.")
    resultado = separar_notas(notas)
    assert resultado.datos_que_faltan == "el precio"
    assert resultado.a_verificar == "la fecha\ny el lugar"
    assert resultado.enfoque == "directo."
    assert resultado.resto == ""


def test_tolera_que_falte_un_apartado():
    resultado = separar_notas("DATOS QUE FALTAN: ninguno\nENFOQUE: cercano.")
    assert resultado.datos_que_faltan == "ninguno"
    assert resultado.a_verificar == ""
    assert resultado.enfoque == "cercano."


def test_tolera_otro_orden_minusculas_y_asteriscos():
    notas = "**Enfoque:** cercano.\n- a verificar: la cifra\n**DATOS QUE FALTAN**: nada"
    resultado = separar_notas(notas)
    assert resultado.enfoque == "cercano."
    assert resultado.a_verificar == "la cifra"
    assert resultado.datos_que_faltan == "nada"


def test_contenido_en_la_linea_siguiente():
    resultado = separar_notas("DATOS QUE FALTAN:\n- el precio\n- el horario\nENFOQUE: x")
    assert resultado.datos_que_faltan == "- el precio\n- el horario"


def test_texto_antes_del_primer_apartado_va_al_resto():
    resultado = separar_notas("Comentario suelto.\nENFOQUE: directo.")
    assert resultado.resto == "Comentario suelto."
    assert resultado.enfoque == "directo."


def test_sin_apartados_todo_va_al_resto():
    resultado = separar_notas("Unas notas sin títulos.")
    assert resultado.resto == "Unas notas sin títulos."
    assert resultado.datos_que_faltan == resultado.a_verificar == resultado.enfoque == ""


def test_notas_vacias_o_none():
    assert separar_notas(None) == separar_notas("")
    assert separar_notas(None).datos_que_faltan == ""


def test_no_confunde_enfoque_dentro_de_una_frase():
    resultado = separar_notas("A VERIFICAR: el enfoque: no es un título aquí")
    assert resultado.a_verificar == "el enfoque: no es un título aquí"
    assert resultado.enfoque == ""


# --- ordenar_problemas y etiqueta ---


def test_orden_graves_codigo_leves():
    problemas = [
        Problema("ADORNO", "m"), Problema("trato", "m"), Problema("GENERAL", "m"),
        Problema("AÑADE", "m"), Problema("hashtags", "m"), Problema("CONTRADICE", "m"),
    ]
    assert [p.regla for p in ordenar_problemas(problemas)] == [
        "AÑADE", "CONTRADICE", "trato", "hashtags", "ADORNO", "GENERAL",
    ]


def test_etiquetas_sin_hablar_de_capas():
    for regla in ("CONTRADICE", "AÑADE", "GENERAL", "ADORNO", "trato", "regla nueva"):
        texto = etiqueta(Problema(regla, "m"))
        assert texto and "capa" not in texto.lower()


# --- resaltar ---


def test_resalta_fuerte_y_suave():
    texto = "Café recién tostado cada mañana."
    html = resaltar(texto, [Problema("ADORNO", "m", "recién tostado"),
                            Problema("AÑADE", "m", "cada mañana")])
    assert f'<mark class="{CLASE_SUAVE}"' in html
    assert f'<mark class="{CLASE_FUERTE}"' in html
    assert ">recién tostado</mark>" in html
    assert ">cada mañana</mark>" in html


def test_las_reglas_de_codigo_resaltan_fuerte():
    html = resaltar("Es revolucionario.", [Problema("expresión vetada", "m", "revolucionario")])
    assert f'<mark class="{CLASE_FUERTE}"' in html


def test_busca_sin_mayusculas_y_con_espacios_y_comillas_unificados():
    texto = "Dijo  «Hola\nMundo» ayer."
    html = resaltar(texto, [Problema("AÑADE", "m", 'dijo "hola mundo"')])
    assert ">Dijo  «Hola\nMundo»</mark>" in html


def test_frase_que_no_esta_no_se_resalta():
    html = resaltar("Texto limpio.", [Problema("AÑADE", "m", "otra cosa")])
    assert html == "Texto limpio."


def test_solape_se_queda_con_la_primera_segun_el_orden():
    texto = "Un café único en el mundo."
    html = resaltar(texto, [Problema("ADORNO", "m", "café único"),
                            Problema("CONTRADICE", "m", "único en el mundo")])
    assert html.count("<mark") == 1
    assert f'<mark class="{CLASE_FUERTE}" title="Contradice el pedido o la ficha">único en el mundo</mark>' in html


def test_escapa_el_html_del_texto():
    texto = '<script>alert("x")</script> & <b>negrita</b>'
    html = resaltar(texto, [Problema("AÑADE", "m", "<b>negrita</b>")])
    assert "<script>" not in html and "<b>" not in html
    assert "&lt;script&gt;" in html and "&amp;" in html
    assert ">&lt;b&gt;negrita&lt;/b&gt;</mark>" in html


def test_no_resalta_problemas_sin_frase_ni_de_notas():
    texto = "Texto con ** asteriscos."
    html = resaltar(texto, [Problema("notas", "m", "**"), Problema("hashtags", "m")])
    assert "<mark" not in html


def test_frase_repetida_resalta_la_primera_aparicion():
    html = resaltar("hoy y hoy", [Problema("AÑADE", "m", "hoy")])
    assert html.startswith("<mark") and html.endswith(" y hoy")
