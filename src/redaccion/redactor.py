"""El redactor general.

Arma el pedido con los bloques de prompts.py y la ficha del cliente, llama
al modelo, separa el texto de las notas y revisa que la respuesta esté
completa. Si falta algo, repite la llamada una vez. Después pasa el texto
por las dos capas del verificador y, si hay problemas corregibles, pide una
reescritura (capa 3) y la vuelve a verificar.
"""

import re
from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from redaccion.clientes import cargar_cliente
from redaccion.llm import obtener_llm
from redaccion.prompts import (
    AJUSTES_INFANTIL,
    AUDIENCIAS,
    BUSCADORES,
    CORRECCION,
    FICHA,
    OBJETIVOS,
    OBJETIVOS_PLATAFORMA,
    PLATAFORMAS,
    SISTEMA,
    USUARIO,
)
from redaccion.verificador import TIPOS_CAPA2, verificar_capa1, verificar_capa2

MAX_INTENTOS = 2
MARCA_NOTAS = re.compile(r"\**\s*NOTAS PARA REVISAR\s*\**", re.IGNORECASE)
SEPARADOR_FINAL = re.compile(r"\n\s*-{3,}\s*$")
TRATO_TEXTO = {"tu": "tú y vosotros", "usted": "usted y ustedes"}
EMOJIS_TEXTO = {"no": "no usa emojis", "moderado": "con moderación",
                "libre": "los usa con libertad"}
TIPOS_CAPA2_CORREGIBLES = {"CONTRADICE", "AÑADE"}


@dataclass
class Pedido:
    """Lo que pide la persona usuaria."""

    tema: str
    plataforma: str
    audiencia: str
    objetivo: str
    cliente: str
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
        cargar_cliente(self.cliente)


@dataclass
class Resultado:
    """Lo que devuelve el redactor.

    texto, notas y problemas son siempre los de la primera versión. Si hubo
    reescritura, la versión corregida está en correccion, con sus propios
    problemas.
    """

    texto: str = ""
    notas: str | None = None
    avisos: list[str] = field(default_factory=list)
    problemas: list = field(default_factory=list)
    descartados: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    tokens_revisor_entrada: int = 0
    tokens_revisor_salida: int = 0
    intentos: int = 0
    correccion: "Resultado | None" = None


def armar_ficha(cliente):
    """Convierte la ficha del cliente en el bloque de texto del prompt."""
    def lista(elementos, vacio):
        return ", ".join(f'"{e}"' for e in elementos) if elementos else vacio

    limites = "\n".join(f"- {limite}" for limite in cliente.limites)
    return FICHA.format(
        nombre=cliente.nombre,
        tipo=cliente.tipo or "sin indicar",
        sector=cliente.sector or "sin indicar",
        descripcion=cliente.descripcion or "sin indicar",
        tono=", ".join(cliente.voz.tono) or "sin indicar",
        trato=TRATO_TEXTO[cliente.voz.trato],
        emojis=EMOJIS_TEXTO.get(cliente.voz.emojis, "sin indicar"),
        expresiones_propias=lista(cliente.voz.expresiones_propias, "ninguna"),
        expresiones_vetadas=lista(cliente.voz.expresiones_vetadas, "ninguna"),
        limites=limites or "- ninguno",
    )


def armar_mensajes(pedido):
    """Devuelve el mensaje de sistema y el de usuario para este pedido."""
    cliente = cargar_cliente(pedido.cliente)
    extras = []
    if pedido.audiencia == "Infantil" and pedido.objetivo in AJUSTES_INFANTIL:
        extras.append(AJUSTES_INFANTIL[pedido.objetivo])
    if pedido.buscadores:
        extras.append(BUSCADORES)

    usuario = USUARIO.format(
        ficha=armar_ficha(cliente),
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


def verificar(resultado, pedido, revisor=None):
    """Pasa el texto por las dos capas y añade lo encontrado al resultado."""
    cliente = cargar_cliente(pedido.cliente)
    resultado.problemas += verificar_capa1(resultado.texto, resultado.notas,
                                           pedido, cliente)
    try:
        revision = verificar_capa2(resultado.texto, pedido, cliente, revisor)
    except Exception as error:
        resultado.avisos.append(
            f"No se pudo hacer la revisión de la capa 2 ({type(error).__name__}). "
            "Revisa los datos del texto a mano."
        )
        return
    resultado.problemas += revision.problemas
    resultado.descartados = revision.descartados
    resultado.tokens_revisor_entrada = revision.tokens_entrada
    resultado.tokens_revisor_salida = revision.tokens_salida


def problemas_a_corregir(problemas):
    """Los de la capa 1 (salvo las notas) y los CONTRADICE y AÑADE de la capa 2."""
    return [
        p for p in problemas
        if p.regla in TIPOS_CAPA2_CORREGIBLES
        or (p.regla not in TIPOS_CAPA2 and p.regla != "notas")
    ]


def listar_problemas(problemas):
    """Lista de problemas en texto, para el mensaje de corrección."""
    lineas = []
    for p in problemas:
        frase = f' "{p.frase}".' if p.frase else ""
        lineas.append(f"- {p.regla}.{frase} {p.motivo}".strip())
    return "\n".join(lineas)


def corregir(resultado, pedido, llm, revisor=None):
    """Capa 3: si hay problemas corregibles, pide una reescritura y la verifica."""
    pendientes = problemas_a_corregir(resultado.problemas)
    if not pendientes:
        return

    original = f"{resultado.texto}\n\nNOTAS PARA REVISAR\n{resultado.notas or ''}"
    mensajes = armar_mensajes(pedido) + [
        AIMessage(content=original),
        HumanMessage(content=CORRECCION.format(problemas=listar_problemas(pendientes))),
    ]
    try:
        respuesta = llm.invoke(mensajes)
    except Exception as error:
        resultado.avisos.append(
            f"No se pudo hacer la reescritura ({type(error).__name__}). "
            "Se entrega solo el texto original."
        )
        return

    uso = respuesta.usage_metadata or {}
    resultado.tokens_entrada += uso.get("input_tokens", 0)
    resultado.tokens_salida += uso.get("output_tokens", 0)

    texto, notas = separar(respuesta.content)
    correccion = Resultado(texto=texto, notas=notas, intentos=1)
    if respuesta.response_metadata.get("finish_reason") == "length":
        correccion.avisos.append(
            "La reescritura puede estar incompleta porque el modelo llegó al límite de tokens."
        )
    verificar(correccion, pedido, revisor)

    resultado.tokens_revisor_entrada += correccion.tokens_revisor_entrada
    resultado.tokens_revisor_salida += correccion.tokens_revisor_salida
    resultado.correccion = correccion


def redactar(pedido, llm=None, verificar_texto=True, revisor=None, reescribir=True):
    """Redacta el pedido y devuelve un Resultado con texto, notas, avisos y problemas."""
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

    if verificar_texto:
        verificar(resultado, pedido, revisor)
        if reescribir:
            corregir(resultado, pedido, llm, revisor)
    return resultado