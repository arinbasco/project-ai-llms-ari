"""Funciones puras para mostrar un Resultado en la interfaz.

Separan las notas en sus apartados, ordenan y nombran los problemas y
resaltan en el texto las frases señaladas. No dependen de Streamlit.
"""

import html
import re
from dataclasses import dataclass

from redaccion.verificador import COMILLAS, normalizar

# --- Notas ---

TITULO_NOTA = re.compile(
    r"^[\s\-*•#]*(DATOS QUE FALTAN|A VERIFICAR|ENFOQUE)[\s*]*:[ \t*]*",
    re.IGNORECASE | re.MULTILINE,
)
CAMPOS_NOTAS = {"DATOS QUE FALTAN": "datos_que_faltan", "A VERIFICAR": "a_verificar",
                "ENFOQUE": "enfoque"}


@dataclass
class Notas:
    """Los tres apartados de las notas. resto es lo que no cae en ninguno."""

    datos_que_faltan: str = ""
    a_verificar: str = ""
    enfoque: str = ""
    resto: str = ""


def limpiar_apartado(texto):
    """Quita espacios y los asteriscos sueltos que deja el Markdown."""
    return texto.strip().strip("*").strip()


def separar_notas(notas):
    """Separa las notas en datos que faltan, a verificar y enfoque.

    Tolera que falte algún apartado, que vengan en otro orden, en minúsculas
    o con asteriscos. Si un apartado se repite, junta su contenido.
    """
    resultado = Notas()
    if not notas:
        return resultado

    titulos = list(TITULO_NOTA.finditer(notas))
    if not titulos:
        resultado.resto = limpiar_apartado(notas)
        return resultado

    resultado.resto = limpiar_apartado(notas[:titulos[0].start()])
    cortes = [titulo.start() for titulo in titulos[1:]] + [len(notas)]
    for titulo, fin in zip(titulos, cortes):
        campo = CAMPOS_NOTAS[titulo.group(1).upper()]
        contenido = limpiar_apartado(notas[titulo.end():fin])
        previo = getattr(resultado, campo)
        setattr(resultado, campo, f"{previo}\n{contenido}".strip())
    return resultado


# --- Problemas ---

TIPOS_GRAVES = ("CONTRADICE", "AÑADE")
TIPOS_LEVES = ("GENERAL", "ADORNO")

ETIQUETAS = {
    "CONTRADICE": "Contradice el pedido o la ficha",
    "AÑADE": "Dato que no está en el pedido ni en la ficha",
    "GENERAL": "Explicación general que no pidió nadie",
    "ADORNO": "Adorno de estilo sin datos",
    "expresión vetada": "Expresión vetada por el cliente",
    "markdown": "Formato que no admite la plataforma",
    "hashtags": "Cantidad de hashtags",
    "emojis": "Emojis donde no van",
    "caracteres en X": "Post demasiado largo para X",
    "hashtags en X": "Hashtags fuera del último post",
    "frase prohibida": "Frase que conviene evitar",
    "trato": "Trato distinto al del cliente",
    "notas": "Notas incompletas",
}

# Reglas cuya frase no sale del texto publicable y no se resaltan.
REGLAS_SIN_RESALTADO = {"notas"}


def etiqueta(problema):
    """Nombre del tipo de problema en lenguaje normal."""
    return ETIQUETAS.get(problema.regla, problema.regla.capitalize())


def prioridad(problema):
    """0 para CONTRADICE y AÑADE, 1 para las reglas de código, 2 para GENERAL y ADORNO."""
    if problema.regla in TIPOS_GRAVES:
        return 0
    if problema.regla in TIPOS_LEVES:
        return 2
    return 1


def ordenar_problemas(problemas):
    """Primero CONTRADICE y AÑADE, después las reglas de código, después GENERAL y ADORNO.

    Dentro de cada grupo se respeta el orden en que llegaron.
    """
    return sorted(problemas, key=prioridad)


# --- Resaltado ---

CLASE_FUERTE = "resaltado-fuerte"
CLASE_SUAVE = "resaltado-suave"


def normalizar_con_posiciones(texto):
    """Normaliza como normalizar() y guarda de qué carácter del original sale cada uno."""
    caracteres, posiciones = [], []
    for indice, caracter in enumerate(texto.translate(COMILLAS)):
        if caracter.isspace():
            if caracteres and caracteres[-1] != " ":
                caracteres.append(" ")
                posiciones.append(indice)
            continue
        for minuscula in caracter.lower():
            caracteres.append(minuscula)
            posiciones.append(indice)
    return "".join(caracteres), posiciones


def buscar_frase(texto_normal, posiciones, frase):
    """Devuelve (inicio, fin) de la frase en el texto original, o None."""
    frase_normal = normalizar(frase)
    if not frase_normal:
        return None
    inicio = texto_normal.find(frase_normal)
    if inicio < 0:
        return None
    fin = inicio + len(frase_normal) - 1
    return posiciones[inicio], posiciones[fin] + 1


def resaltar(texto, problemas):
    """Devuelve el texto en HTML con las frases señaladas dentro de <mark>.

    El texto se escapa entero, así que nunca se interpreta como HTML. Las
    frases se buscan como en el filtro de citas de la capa 2: sin distinguir
    mayúsculas y con espacios y comillas unificados. Las que no aparecen no se
    resaltan. Se recorren en el orden de ordenar_problemas(); si una se solapa
    con otra ya resaltada, se deja sin resaltar.
    """
    texto_normal, posiciones = normalizar_con_posiciones(texto)
    marcas = []
    for problema in ordenar_problemas(problemas):
        if not problema.frase or problema.regla in REGLAS_SIN_RESALTADO:
            continue
        tramo = buscar_frase(texto_normal, posiciones, problema.frase)
        if tramo is None:
            continue
        inicio, fin = tramo
        if any(inicio < otro_fin and otro_inicio < fin
               for otro_inicio, otro_fin, _ in marcas):
            continue
        marcas.append((inicio, fin, problema))

    partes, actual = [], 0
    for inicio, fin, problema in sorted(marcas, key=lambda marca: marca[0]):
        clase = CLASE_SUAVE if problema.regla in TIPOS_LEVES else CLASE_FUERTE
        partes.append(html.escape(texto[actual:inicio], quote=False))
        partes.append(f'<mark class="{clase}" title="{html.escape(etiqueta(problema))}">'
                      f"{html.escape(texto[inicio:fin], quote=False)}</mark>")
        actual = fin
    partes.append(html.escape(texto[actual:], quote=False))
    return "".join(partes)


# --- Errores del redactor ---

ERRORES_REDACTOR = {
    "RateLimitError": "Se ha agotado la cuota del modelo. Prueba de nuevo más tarde.",
    "APITimeoutError": "El modelo tardó demasiado en responder. Vuelve a intentarlo.",
    "APIConnectionError": "No hay conexión con el servicio del modelo. Comprueba la "
                          "conexión y vuelve a intentarlo.",
    "AuthenticationError": "La clave de Groq no es válida. Revisa los secretos de la aplicación.",
    "NotFoundError": "El modelo indicado en GROQ_MODEL no existe. Revisa los secretos "
                     "de la aplicación.",
    "InternalServerError": "El servicio del modelo ha fallado. Vuelve a intentarlo en unos "
                           "minutos.",
}


def mensaje_error_redactor(error):
    """Explica en lenguaje normal por qué no respondió el redactor.

    Se busca por nombre de clase, también en las clases padre, para no
    depender de importar las excepciones de Groq.
    """
    for clase in type(error).__mro__:
        if clase.__name__ in ERRORES_REDACTOR:
            return ERRORES_REDACTOR[clase.__name__]
    if isinstance(error, ValueError):  # Falta GROQ_MODEL u otra configuración.
        return f"Falta configuración: {error}"
    return f"No se pudo redactar el texto ({type(error).__name__}). Vuelve a intentarlo."
