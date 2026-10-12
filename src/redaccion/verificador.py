"""Verificador del texto generado.

Capa 1: reglas que se comprueban con código, sin llamar al modelo.
Capa 2: revisión con un segundo modelo, que señala lo que el texto dice
más allá del pedido y la ficha.

Varias listas de este archivo copian reglas de prompts.py. Si cambian
allí, hay que cambiarlas aquí.
"""

import re
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from redaccion.llm import obtener_revisor
from redaccion.prompts import REVISOR, REVISOR_USUARIO


@dataclass
class Problema:
    """Un fallo encontrado en el texto."""

    regla: str
    motivo: str
    frase: str = ""


def buscar_expresion(texto, expresion):
    """Busca una expresión exacta, sin distinguir mayúsculas.

    Exige borde de palabra solo donde la expresión empieza o termina con
    letra o número, para que funcione también con "¿qué opináis?".
    """
    inicio = r"\b" if expresion[:1].isalnum() else ""
    fin = r"\b" if expresion[-1:].isalnum() else ""
    return re.search(inicio + re.escape(expresion) + fin, texto, re.IGNORECASE)


# --- Regla 1. Expresiones vetadas de la ficha ---

def revisar_vetadas(texto, vetadas):
    """Busca en el texto las expresiones vetadas de la ficha."""
    problemas = []
    for expresion in vetadas:
        encontrada = buscar_expresion(texto, expresion)
        if encontrada:
            problemas.append(Problema(
                regla="expresión vetada",
                motivo=f'La ficha veta la expresión "{expresion}".',
                frase=encontrada.group(0),
            ))
    return problemas


# --- Regla 2. Markdown fuera del blog ---

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


# --- Regla 3. Hashtags según plataforma y audiencia ---

HASHTAG = re.compile(r"(?<!\w)#\w+")

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


# --- Regla 4. Emojis donde no van ---

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\U0001F1E6-\U0001F1FF]")
PLATAFORMAS_SIN_EMOJIS = {"LinkedIn", "Blog"}
AUDIENCIAS_SIN_EMOJIS = {"Profesional", "Institucional"}


def revisar_emojis(texto, plataforma, audiencia, emojis_ficha):
    """Gana la indicación más restrictiva entre ficha, plataforma y audiencia."""
    prohiben = []
    if emojis_ficha == "no":
        prohiben.append("la ficha del cliente")
    if plataforma in PLATAFORMAS_SIN_EMOJIS:
        prohiben.append(f"la plataforma {plataforma}")
    if audiencia in AUDIENCIAS_SIN_EMOJIS:
        prohiben.append(f"la audiencia {audiencia}")
    if not prohiben:
        return []

    encontrados = EMOJI.findall(texto)
    if not encontrados:
        return []
    return [Problema(
        regla="emojis",
        motivo=f"Hay emojis y no los permite {' ni '.join(prohiben)}.",
        frase="".join(encontrados),
    )]


# --- Regla 5. Posts de X ---

MAX_CARACTERES_X = 260
NUMERACION = re.compile(r"\b(\d+)/(\d+)\b")


def partir_posts(texto):
    """Parte un hilo de X en posts usando la numeración 1/4, 2/4...

    Solo lo trata como hilo si hay al menos dos marcas seguidas y con el
    mismo total. Acepta la numeración al principio o al final de cada post.
    Si no es un hilo, devuelve el texto entero como un solo post.
    """
    texto = texto.strip()
    marcas = list(NUMERACION.finditer(texto))
    total = len(marcas)
    es_hilo = total >= 2 and all(
        int(marca.group(1)) == i + 1 and int(marca.group(2)) == total
        for i, marca in enumerate(marcas)
    )
    if not es_hilo:
        return [texto]

    if texto.startswith(marcas[0].group(0)):
        cortes = [marca.start() for marca in marcas] + [len(texto)]
    else:
        cortes = [0] + [marca.end() for marca in marcas[:-1]] + [len(texto)]
    return [texto[a:b].strip() for a, b in zip(cortes, cortes[1:])]


def revisar_x(texto):
    """Cada post con 260 caracteres como máximo y hashtags solo en el último."""
    posts = partir_posts(texto)
    problemas = []
    for numero, post in enumerate(posts, start=1):
        if len(post) > MAX_CARACTERES_X:
            problemas.append(Problema(
                regla="caracteres en X",
                motivo=(f"El post {numero} tiene {len(post)} caracteres y el "
                        f"máximo es {MAX_CARACTERES_X}."),
                frase=post[:60],
            ))
    for numero, post in enumerate(posts[:-1], start=1):
        hashtags = HASHTAG.findall(post)
        if hashtags:
            problemas.append(Problema(
                regla="hashtags en X",
                motivo=f"El post {numero} lleva hashtags y en X solo van en el último.",
                frase=" ".join(hashtags),
            ))
    return problemas


# --- Regla 6. Frases que los prompts piden evitar ---

FRASES_PROHIBIDAS = {
    "todas": ["se erige como", "presume de", "no es solo",
              "los expertos", "muchos coinciden"],
    "Informar": ["esto es lo que pasó", "no vas a creer", "histórico",
                 "polémico", "impactante"],
    "Vender": ["el mejor", "la mejor", "único", "única", "inigualable",
               "últimas unidades", "solo hoy"],
    "Generar conversación": ["comenta sí", "etiqueta a alguien", "dale like",
                             "comparte si", "¿qué opináis?"],
    "Convocar": ["plazas limitadas", "últimas entradas"],
    "Infantil": ["solo hoy", "corre", "todos tus amigos"],
    "Profesional": ["disruptivo", "sinergia", "transformador", "ecosistema"],
    "Divulgación": ["lo que nadie te cuenta", "cambiará todo"],
    "Institucional": ["da comienzo", "es por ello que"],
}


def revisar_frases_prohibidas(texto, objetivo, audiencia, tema):
    """Busca las frases prohibidas, salvo las que vienen en el propio pedido."""
    frases = []
    for clave in ("todas", objetivo, audiencia):
        for frase in FRASES_PROHIBIDAS.get(clave, []):
            if frase not in frases:
                frases.append(frase)

    problemas = []
    for frase in frases:
        if buscar_expresion(tema, frase):
            continue
        encontrada = buscar_expresion(texto, frase)
        if encontrada:
            problemas.append(Problema(
                regla="frase prohibida",
                motivo=f'El prompt pide evitar "{frase}".',
                frase=encontrada.group(0),
            ))
    return problemas


# --- Regla 7. Trato contrario al de la ficha ---

MARCAS_USTED = re.compile(r"\b(usted|ustedes)\b", re.IGNORECASE)
MARCAS_TU = re.compile(
    r"\b(tú|tu|tus|te|contigo|vosotros|vosotras|os|vuestro|vuestra|vuestros|vuestras)\b",
    re.IGNORECASE,
)


def revisar_trato(texto, trato_ficha, audiencia):
    """Busca pronombres del trato contrario. No detecta formas verbales."""
    esperado = "tu" if audiencia == "Infantil" else trato_ficha
    patron = MARCAS_USTED if esperado == "tu" else MARCAS_TU
    encontrada = patron.search(texto)
    if not encontrada:
        return []
    trato_texto = "tú" if esperado == "tu" else "usted"
    return [Problema(
        regla="trato",
        motivo=f"El texto debería tratar de {trato_texto} y usa \"{encontrada.group(0)}\".",
        frase=encontrada.group(0),
    )]


# --- Regla 8. Notas completas ---

TITULOS_NOTAS = ("DATOS QUE FALTAN", "A VERIFICAR", "ENFOQUE")


def revisar_notas(notas):
    """Las tres notas presentes y en texto plano."""
    if notas is None:
        return []  # Si faltan del todo, ya avisa el redactor.

    problemas = [
        Problema(regla="notas", motivo=f'Falta la nota "{titulo}".')
        for titulo in TITULOS_NOTAS
        if titulo.lower() not in notas.lower()
    ]
    for patron, descripcion in MARCAS_MARKDOWN:
        encontrada = patron.search(notas)
        if encontrada:
            problemas.append(Problema(
                regla="notas",
                motivo=f"Las notas llevan {descripcion} y van en texto plano.",
                frase=encontrada.group(0).strip(),
            ))
    return problemas


# --- Todas juntas ---

def verificar_capa1(texto, notas, pedido, cliente):
    """Pasa todas las reglas de la capa 1 y devuelve la lista de problemas."""
    problemas = []
    problemas += revisar_vetadas(texto, cliente.voz.expresiones_vetadas)
    problemas += revisar_markdown(texto, pedido.plataforma)
    problemas += revisar_hashtags(texto, pedido.plataforma, pedido.audiencia)
    problemas += revisar_emojis(texto, pedido.plataforma, pedido.audiencia,
                                cliente.voz.emojis)
    if pedido.plataforma == "X":
        problemas += revisar_x(texto)
    problemas += revisar_frases_prohibidas(texto, pedido.objetivo,
                                           pedido.audiencia, pedido.tema)
    problemas += revisar_trato(texto, cliente.voz.trato, pedido.audiencia)
    problemas += revisar_notas(notas)
    return problemas

    # --- Capa 2. Revisión con un segundo modelo ---

TIPOS_CAPA2 = ("CONTRADICE", "AÑADE", "GENERAL", "ADORNO")
CAMPO = re.compile(r"^\s*[-•]?\s*(FRASE|TIPO|MOTIVO)\s*:\s*(.*)$", re.IGNORECASE)
SEPARADOR_BLOQUES = re.compile(r"\n\s*\n")
COMILLAS = str.maketrans({"“": '"', "”": '"', "«": '"', "»": '"', "‘": "'", "’": "'"})


@dataclass
class Revision:
    """Lo que devuelve la capa 2."""

    problemas: list
    descartados: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0


def armar_mensajes_revisor(texto, pedido, cliente):
    """Mensaje de sistema y de usuario para el revisor."""
    usuario = REVISOR_USUARIO.format(
        nombre=cliente.nombre,
        descripcion=cliente.descripcion or "sin indicar",
        tema=pedido.tema.strip(),
        texto=texto,
    )
    return [SystemMessage(content=REVISOR), HumanMessage(content=usuario)]


def leer_revision(contenido):
    """Convierte la respuesta del revisor en problemas.

    Devuelve los problemas y cuántos bloques venían mal formados.
    """
    if contenido.strip().strip(".").upper() == "NINGUNO":
        return [], 0

    problemas, mal_formados = [], 0
    for bloque in SEPARADOR_BLOQUES.split(contenido.strip()):
        campos = {}
        for linea in bloque.replace("*", "").splitlines():
            encontrado = CAMPO.match(linea)
            if encontrado:
                campos[encontrado.group(1).upper()] = encontrado.group(2).strip()

        tipo = campos.get("TIPO", "").upper().strip(" .")
        frase = campos.get("FRASE", "").strip().strip('"“”«»')
        if not frase or tipo not in TIPOS_CAPA2:
            mal_formados += 1
            continue
        problemas.append(Problema(regla=tipo, motivo=campos.get("MOTIVO", ""),
                                  frase=frase))
    return problemas, mal_formados


def normalizar(texto):
    """Minúsculas, comillas unificadas y espacios unificados."""
    return re.sub(r"\s+", " ", texto.translate(COMILLAS)).strip().lower()


def filtrar_citas(problemas, texto):
    """Se queda solo con los problemas cuya frase está de verdad en el texto."""
    texto_normal = normalizar(texto)
    validos = [p for p in problemas if normalizar(p.frase) in texto_normal]
    return validos, len(problemas) - len(validos)


def verificar_capa2(texto, pedido, cliente, llm=None):
    """Pide al revisor que señale lo que el texto dice más allá del pedido y la ficha."""
    llm = llm or obtener_revisor()
    respuesta = llm.invoke(armar_mensajes_revisor(texto, pedido, cliente))
    uso = respuesta.usage_metadata or {}

    problemas, mal_formados = leer_revision(respuesta.content)
    validos, citas_falsas = filtrar_citas(problemas, texto)
    return Revision(
        problemas=validos,
        descartados=mal_formados + citas_falsas,
        tokens_entrada=uso.get("input_tokens", 0),
        tokens_salida=uso.get("output_tokens", 0),
    )