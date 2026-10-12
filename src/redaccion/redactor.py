"""El redactor general.

Arma el pedido con los bloques de prompts.py, llama al modelo, separa el
texto de las notas y revisa que la respuesta esté completa. Si falta algo,
repite la llamada una vez y, si sigue mal, entrega lo que hay con un aviso.
"""

import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage

from redaccion.llm import obtener_llm
from redaccion.prompts import (
    AJUSTES_INFANTIL,
    AUDIENCIAS,
    BUSCADORES,
    OBJETIVOS,
    OBJETIVOS_PLATAFORMA,
    PLATAFORMAS,
    SISTEMA,
    USUARIO,
)

MAX_INTENTOS = 2
MARCA_NOTAS = re.compile(r"\**\s*NOTAS PARA REVISAR\s*\**", re.IGNORECASE)
SEPARADOR_FINAL = re.compile(r"\n\s*-{3,}\s*$")


@dataclass
class Pedido:
    """Lo que pide la persona usuaria."""

    tema: str
    plataforma: str
    audiencia: str
    objetivo: str
    buscadores: bool = False

    def validar(self):
        """Lanza ValueError si el pedido no se puede redactar."""
        if not self.tema or not self.tema.strip():
            raise ValueError("Escribe el tema del pedido.")
        if self.plataforma not in PLATAFORMAS:
            raise ValueError(f"Plataforma desconocida: {self.plataforma}")
        if self.audiencia not in AUDIENCIAS:
            raise ValueError(f"Audiencia desconocida: {self.audiencia}")
        if self.objetivo not in OBJETIVOS:
            raise ValueError(f"Objetivo desconocido: {self.objetivo}")


@dataclass
class Resultado:
    """Lo que devuelve el redactor."""

    texto: str = ""
    notas: str | None = None
    avisos: list[str] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_salida: int = 0
    intentos: int = 0


def armar_mensajes(pedido):
    """Devuelve el mensaje de sistema y el de usuario para este pedido."""
    extras = []
    if pedido.audiencia == "Infantil" and pedido.objetivo in AJUSTES_INFANTIL:
        extras.append(AJUSTES_INFANTIL[pedido.objetivo])
    if pedido.buscadores:
        extras.append(BUSCADORES)

    usuario = USUARIO.format(
        tema=pedido.tema.strip(),
        plataforma=PLATAFORMAS[pedido.plataforma],
        audiencia=AUDIENCIAS[pedido.audiencia],
        objetivo=OBJETIVOS[pedido.objetivo],
        objetivo_plataforma=OBJETIVOS_PLATAFORMA[pedido.objetivo][pedido.plataforma],
        extras="\n".join(extras),
    )
    return [SystemMessage(content=SISTEMA), HumanMessage(content=usuario)]


def separar(contenido):
    """Separa el texto publicable de las notas. Si no hay notas, devuelve None."""
    partes = MARCA_NOTAS.split(contenido, maxsplit=1)
    texto = SEPARADOR_FINAL.sub("", partes[0].strip()).strip()
    notas = partes[1].strip() if len(partes) > 1 else None
    return texto, notas or None


def redactar(pedido, llm=None):
    """Redacta el pedido y devuelve un Resultado con texto, notas y avisos."""
    pedido.validar()
    llm = llm or obtener_llm()
    mensajes = armar_mensajes(pedido)
    resultado = Resultado()

    for intento in range(1, MAX_INTENTOS + 1):
        respuesta = llm.invoke(mensajes)

        uso = respuesta.usage_metadata or {}
        resultado.tokens_entrada += uso.get("input_tokens", 0)
        resultado.tokens_salida += uso.get("output_tokens", 0)
        resultado.intentos = intento

        cortado = respuesta.response_metadata.get("finish_reason") == "length"
        resultado.texto, resultado.notas = separar(respuesta.content)

        if not cortado and resultado.notas:
            break

    if cortado:
        resultado.avisos.append(
            "El texto puede estar incompleto porque el modelo llegó al límite de tokens."
        )
    if not resultado.notas:
        resultado.avisos.append(
            "El modelo no escribió las notas para revisar. Comprueba datos y afirmaciones a mano."
        )
    return resultado