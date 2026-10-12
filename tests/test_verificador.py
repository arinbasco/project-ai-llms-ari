"""Pruebas de la capa 1 del verificador."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.verificador import revisar_hashtags, revisar_markdown, revisar_vetadas


def test_vetada_se_detecta_sin_importar_mayusculas():
    problemas = revisar_vetadas("Un rendimiento Garantizado.", ["garantizado"])
    assert len(problemas) == 1
    assert problemas[0].frase == "Garantizado"


def test_vetada_no_salta_dentro_de_otra_palabra():
    assert revisar_vetadas("La reconquista del barrio.", ["conquista"]) == []


def test_sin_vetadas_no_hay_problemas():
    assert revisar_vetadas("Un café recién tostado.", []) == []


def test_markdown_fuera_del_blog_se_detecta():
    problemas = revisar_markdown("**Oferta** de hoy", "Instagram")
    assert len(problemas) == 1
    assert problemas[0].regla == "markdown"


def test_markdown_en_el_blog_esta_permitido():
    assert revisar_markdown("# Título\n\n**Oferta** de hoy", "Blog") == []


def test_hashtags_no_cuentan_como_titulos():
    assert revisar_markdown("Pásate a probarlo.\n\n#café #tostadero", "Instagram") == []


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