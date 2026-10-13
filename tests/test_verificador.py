"""Pruebas de la capa 1 del verificador."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage

from redaccion.clientes import cargar_cliente
from redaccion.redactor import Pedido
from redaccion.verificador import (
    partir_posts,
    revisar_emojis,
    revisar_frases_prohibidas,
    revisar_hashtags,
    revisar_markdown,
    revisar_notas,
    revisar_trato,
    revisar_vetadas,
    revisar_x,
    verificar_capa1,
    verificar_capa2,
)

NOTAS_COMPLETAS = "DATOS QUE FALTAN: ninguno\nA VERIFICAR: ninguna\nENFOQUE: directo."


# Regla 1. Vetadas

def test_vetada_se_detecta_sin_importar_mayusculas():
    problemas = revisar_vetadas("Un rendimiento Garantizado.", ["garantizado"])
    assert len(problemas) == 1
    assert problemas[0].frase == "Garantizado"


def test_vetada_no_salta_dentro_de_otra_palabra():
    assert revisar_vetadas("La reconquista del barrio.", ["conquista"]) == []


def test_sin_vetadas_no_hay_problemas():
    assert revisar_vetadas("Un café recién tostado.", []) == []


# Regla 2. Markdown

def test_markdown_fuera_del_blog_se_detecta():
    problemas = revisar_markdown("**Oferta** de hoy", "Instagram")
    assert len(problemas) == 1
    assert problemas[0].regla == "markdown"


def test_markdown_en_el_blog_esta_permitido():
    assert revisar_markdown("# Título\n\n**Oferta** de hoy", "Blog") == []


def test_hashtags_no_cuentan_como_titulos():
    assert revisar_markdown("Pásate a probarlo.\n\n#café #tostadero", "Instagram") == []


# Regla 3. Hashtags

def test_hashtags_en_rango_no_dan_problema():
    texto = "Café recién tostado.\n\n#café #tostadero #madrid #barrio"
    assert revisar_hashtags(texto, "Instagram", "Público general") == []


def test_pocos_hashtags_en_instagram():
    problemas = revisar_hashtags("Café.\n\n#café", "Instagram", "Público general")
    assert len(problemas) == 1
    assert problemas[0].frase == "#café"


def test_demasiados_hashtags_en_x():
    texto = "Café recién tostado. #café #tostadero #madrid"
    assert len(revisar_hashtags(texto, "X", "Público general")) == 1


def test_blog_sin_hashtags_y_con_titulos():
    texto = "# Título\n\n## Subtítulo\n\nTexto del artículo."
    assert revisar_hashtags(texto, "Blog", "Público general") == []


def test_hashtag_en_el_blog_da_problema():
    texto = "# Título\n\nTexto del artículo. #café"
    assert len(revisar_hashtags(texto, "Blog", "Público general")) == 1


def test_institucional_permite_uno_aunque_instagram_pida_tres():
    texto = "Abrimos la convocatoria.\n\n#UniversidadMunin"
    assert revisar_hashtags(texto, "Instagram", "Institucional") == []


# Regla 4. Emojis

def test_emoji_con_ficha_que_no_los_usa():
    problemas = revisar_emojis("Pásese por la app ☕", "Instagram", "Público general", "no")
    assert len(problemas) == 1
    assert "ficha" in problemas[0].motivo


def test_emoji_permitido_con_moderacion():
    assert revisar_emojis("Recién tostado ☕", "Instagram", "Público general", "moderado") == []


def test_emoji_en_linkedin_aunque_la_ficha_los_permita():
    assert len(revisar_emojis("Novedades ☕", "LinkedIn", "Público general", "libre")) == 1


# Regla 5. Posts de X

def test_post_unico_demasiado_largo():
    problemas = revisar_x("a" * 300)
    assert len(problemas) == 1
    assert problemas[0].regla == "caracteres en X"


def test_hilo_numerado_al_principio():
    texto = "1/2 Primer post.\n\n2/2 Segundo post. #café"
    assert partir_posts(texto) == ["1/2 Primer post.", "2/2 Segundo post. #café"]
    assert revisar_x(texto) == []


def test_hilo_numerado_al_final():
    texto = "Primer post. 1/2\n\nSegundo post. 2/2\n#café"
    assert len(partir_posts(texto)) == 2
    assert revisar_x(texto) == []


def test_hashtag_fuera_del_ultimo_post():
    texto = "1/2 Primer post #café\n\n2/2 Segundo post."
    problemas = revisar_x(texto)
    assert len(problemas) == 1
    assert problemas[0].regla == "hashtags en X"


def test_una_fraccion_no_es_un_hilo():
    assert partir_posts("Llévate 1/2 kilo de café.") == ["Llévate 1/2 kilo de café."]


# Regla 6. Frases prohibidas

def test_frase_prohibida_en_vender():
    problemas = revisar_frases_prohibidas("El mejor café del barrio.", "Vender",
                                          "Público general", "bolsa de café")
    assert len(problemas) == 1


def test_frase_prohibida_permitida_si_viene_en_el_pedido():
    assert revisar_frases_prohibidas("Solo hoy, bolsa a 10 euros.", "Vender",
                                     "Público general", "oferta solo hoy") == []


def test_pregunta_prohibida_con_signo_de_apertura():
    problemas = revisar_frases_prohibidas("Nuevo horario. ¿Qué opináis?",
                                          "Generar conversación",
                                          "Público general", "nuevo horario")
    assert len(problemas) == 1


def test_texto_limpio_sin_frases_prohibidas():
    assert revisar_frases_prohibidas("Café recién tostado.", "Informar",
                                     "Público general", "café") == []


# Regla 7. Trato

def test_usted_en_un_cliente_de_tu():
    assert len(revisar_trato("Le esperamos, usted decide.", "tu", "Público general")) == 1


def test_tu_en_un_cliente_de_usted():
    assert len(revisar_trato("Ven con tus amigos.", "usted", "Público general")) == 1


def test_infantil_siempre_es_de_tu():
    assert revisar_trato("Ven con tus amigos.", "usted", "Infantil") == []


# Regla 8. Notas

def test_notas_completas():
    assert revisar_notas(NOTAS_COMPLETAS) == []


def test_falta_una_nota():
    problemas = revisar_notas("DATOS QUE FALTAN: ninguno\nA VERIFICAR: ninguna")
    assert len(problemas) == 1
    assert "ENFOQUE" in problemas[0].motivo


def test_notas_con_markdown():
    notas = "**DATOS QUE FALTAN:** ninguno\nA VERIFICAR: ninguna\nENFOQUE: directo."
    assert len(revisar_notas(notas)) == 1


def test_sin_notas_no_repite_el_aviso_del_redactor():
    assert revisar_notas(None) == []


# Todas juntas

def test_verificar_capa1_junta_las_reglas():
    pedido = Pedido("café", "Instagram", "Público general", "Vender", "banco-faro")
    cliente = cargar_cliente("banco-faro")
    problemas = verificar_capa1("Café **garantizado** ☕", NOTAS_COMPLETAS, pedido, cliente)
    reglas = {problema.regla for problema in problemas}
    assert {"expresión vetada", "markdown", "emojis", "hashtags"} <= reglas

# Capa 2

TEXTO_BLOG = "La Universidad Munin publicará el informe completo. Un aroma intenso."
PEDIDO_UNI = Pedido("estudio sobre árboles y temperatura", "Blog", "Divulgación",
                    "Informar", "universidad-munin")
CLIENTE_UNI = cargar_cliente("universidad-munin")


def revisar_con(respuesta, texto=TEXTO_BLOG):
    """Pasa el texto por la capa 2 con un revisor falso que da esta respuesta."""
    llm = FakeListChatModel(responses=[respuesta])
    return verificar_capa2(texto, PEDIDO_UNI, CLIENTE_UNI, llm)


def test_capa2_ninguno():
    revision = revisar_con("NINGUNO")
    assert revision.problemas == []
    assert revision.descartados == 0


def test_capa2_lee_dos_bloques():
    respuesta = ("FRASE: la Universidad Munin publicará el informe completo\n"
                 "TIPO: AÑADE\n"
                 "MOTIVO: el pedido no menciona ningún informe\n\n"
                 "FRASE: aroma intenso\n"
                 "TIPO: ADORNO\n"
                 "MOTIVO: adjetivo sin dato")
    revision = revisar_con(respuesta)
    assert [p.regla for p in revision.problemas] == ["AÑADE", "ADORNO"]
    assert revision.descartados == 0


def test_capa2_descarta_citas_falsas():
    revision = revisar_con("FRASE: el informe se publicó ayer\nTIPO: CONTRADICE\nMOTIVO: x")
    assert revision.problemas == []
    assert revision.descartados == 1


def test_capa2_acepta_mayusculas_y_espacios():
    revision = revisar_con(
        "FRASE: la universidad munin publicará   el informe completo\nTIPO: AÑADE\nMOTIVO: x"
    )
    assert len(revision.problemas) == 1


def test_capa2_descarta_bloques_mal_formados():
    respuesta = ("FRASE: aroma intenso\nMOTIVO: falta el tipo\n\n"
                 "FRASE: aroma intenso\nTIPO: OPINION\nMOTIVO: tipo inventado")
    revision = revisar_con(respuesta)
    assert revision.problemas == []
    assert revision.descartados == 2


def test_capa2_tolera_negritas():
    revision = revisar_con("**FRASE:** aroma intenso\n**TIPO:** ADORNO\n**MOTIVO:** adjetivo")
    assert len(revision.problemas) == 1

class RevisorFijo:
    """Revisor falso que devuelve siempre el mismo mensaje, ya construido."""

    def __init__(self, mensaje):
        self.mensaje = mensaje

    def invoke(self, mensajes):
        return self.mensaje


def test_capa2_guarda_el_razonamiento():
    mensaje = AIMessage(content="NINGUNO",
                        additional_kwargs={"reasoning_content": "Reviso frase por frase."})
    revision = verificar_capa2(TEXTO_BLOG, PEDIDO_UNI, CLIENTE_UNI, RevisorFijo(mensaje))
    assert revision.razonamiento == "Reviso frase por frase."


def test_capa2_ignora_el_razonamiento_dentro_del_texto():
    contenido = ("<think>FRASE: algo inventado\nTIPO: AÑADE\nMOTIVO: pensando</think>"
                 "FRASE: aroma intenso\nTIPO: ADORNO\nMOTIVO: adjetivo")
    revision = verificar_capa2(TEXTO_BLOG, PEDIDO_UNI, CLIENTE_UNI,
                               RevisorFijo(AIMessage(content=contenido)))
    assert [p.frase for p in revision.problemas] == ["aroma intenso"]
    assert revision.descartados == 0