"""Verificador del texto generado.

Capa 1: reglas que se comprueban con código, sin llamar al modelo.
Capa 2 (pendiente): revisión con un segundo modelo.
"""

import re
from dataclasses import dataclass


@dataclass
class Problema:
    """Un fallo encontrado en el texto."""

    regla: str
    motivo: str
    frase: str = ""


def revisar_vetadas(texto, vetadas):
    """Busca en el texto las expresiones vetadas de la ficha."""
    problemas = []
    for expresion in vetadas:
        patron = r"\b" + re.escape(expresion) + r"\b"
        encontrada = re.search(patron, texto, re.IGNORECASE)
        if encontrada:
            problemas.append(Problema(
                regla="expresión vetada",
                motivo=f'La ficha veta la expresión "{expresion}".',
                frase=encontrada.group(0),
            ))
    return problemas


MARCAS_MARKDOWN = [
    (re.compile(r"\*\*?[^\s*]"), "asteriscos de negrita o cursiva"),
    (re.compile(r"^#{1,6}\s", re.MULTILINE), "título con almohadilla"),
    (re.compile(r"^\s*-{3,}\s*$", re.MULTILINE), "línea de guiones"),
]


def revisar_markdown(texto, plataforma):
    """Fuera del blog, el texto va en texto plano, sin Markdown."""
    if plataforma == "Blog":
        return []
    problemas = []
    for patron, descripcion in MARCAS_MARKDOWN:
        encontrada = patron.search(texto)
        if encontrada:
            problemas.append(Problema(
                regla="markdown",
                motivo=f"Hay {descripcion} en un texto para {plataforma}.",
                frase=encontrada.group(0).strip(),
            ))
    return problemas


HASHTAG = re.compile(r"(?<!\w)#\w+")

# Copia de lo que piden PLATAFORMAS y AUDIENCIAS["Institucional"] en
# prompts.py. Si cambian allí, hay que cambiarlos aquí.
LIMITES_HASHTAGS = {
    "X": (1, 2),
    "Instagram": (3, 6),
    "LinkedIn": (0, 3),
    "Blog": (0, 0),
}
LIMITE_HASHTAGS_INSTITUCIONAL = (0, 1)


def revisar_hashtags(texto, plataforma, audiencia):
    """Comprueba que la cantidad de hashtags encaja con plataforma y audiencia."""
    hashtags = HASHTAG.findall(texto)
    cantidad = len(hashtags)

    minimo, maximo = LIMITES_HASHTAGS[plataforma]
    if audiencia == "Institucional":
        minimo, maximo = LIMITE_HASHTAGS_INSTITUCIONAL[0], min(
            maximo, LIMITE_HASHTAGS_INSTITUCIONAL[1]
        )

    if minimo <= cantidad <= maximo:
        return []

    if maximo == 0:
        motivo = f"En {plataforma} no van hashtags y hay {cantidad}."
    else:
        motivo = (f"Para {plataforma} y audiencia {audiencia} van entre "
                  f"{minimo} y {maximo} hashtags, y hay {cantidad}.")
    return [Problema(regla="hashtags", motivo=motivo, frase=" ".join(hashtags))]