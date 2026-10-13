"""La Redacción: interfaz web del redactor de Digital Content.

Se arranca con: streamlit run app.py
"""

import base64
import html
import os
import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from redaccion.clientes import listar_clientes  # noqa: E402
from redaccion.prompts import AUDIENCIAS, OBJETIVOS, PLATAFORMAS  # noqa: E402
from redaccion.presentacion import (  # noqa: E402
    TIPOS_LEVES,
    etiqueta,
    mensaje_error_redactor,
    ordenar_problemas,
    resaltar,
    separar_notas,
)
from redaccion.redactor import (  # noqa: E402
    CORRIGIENDO,
    EMOJIS_TEXTO,
    REDACTANDO,
    REVISANDO,
    REVISANDO_CORRECCION,
    TRATO_TEXTO,
    Pedido,
    redactar,
)

LOGO = RAIZ / "assets" / "logo.svg"
ESTILOS = RAIZ / "assets" / "estilos.css"

ETAPAS = {
    REDACTANDO: "Redactando el texto",
    REVISANDO: "Revisando el texto",
    CORRIGIENDO: "Corrigiendo los problemas encontrados",
    REVISANDO_CORRECCION: "Revisando la corrección",
}


# --- Piezas de la página ---

def poner_estilos():
    st.markdown(f"<style>{ESTILOS.read_text(encoding='utf-8')}</style>",
                unsafe_allow_html=True)


def cabecera():
    """Logo, nombre de la agencia y nombre de la herramienta."""
    logo = base64.b64encode(LOGO.read_bytes()).decode()
    st.markdown(
        '<div class="cabecera">'
        f'<img src="data:image/svg+xml;base64,{logo}" alt="">'
        '<div><div class="marca">Digital Content</div>'
        '<div class="submarca">La Redacción</div></div></div>',
        unsafe_allow_html=True,
    )


def texto_plano(texto):
    """Muestra texto sin interpretarlo como Markdown ni HTML, con sus saltos de línea."""
    st.markdown(f'<div class="texto-plano">{html_en_linea(html.escape(texto))}</div>',
                unsafe_allow_html=True)


def html_en_linea(fragmento):
    """Cambia los saltos de línea por <br> para que el Markdown no toque el bloque."""
    return fragmento.replace("\r\n", "\n").replace("\n", "<br>")


def ficha_cliente(cliente):
    """Resumen plegado de la ficha del cliente elegido."""
    voz = cliente.voz

    def lista(elementos):
        return ", ".join(elementos) if elementos else "ninguna"

    with st.expander("Ficha del cliente", expanded=False):
        lineas = [
            f"Trato: {TRATO_TEXTO[voz.trato]}",
            f"Tono: {', '.join(voz.tono) or 'sin indicar'}",
            f"Expresiones propias: {lista(voz.expresiones_propias)}",
            f"Expresiones vetadas: {lista(voz.expresiones_vetadas)}",
            f"Emojis: {EMOJIS_TEXTO.get(voz.emojis, 'sin indicar')}",
            "Límites:",
        ]
        lineas += [f"- {limite}" for limite in cliente.limites] or ["- ninguno"]
        texto_plano("\n".join(lineas))


def formulario():
    """Formulario de la barra lateral. Devuelve los datos del pedido y si se pulsó Redactar.

    Los valores se guardan por clave en la sesión, así que se conservan
    después de generar.
    """
    clientes = {cliente.id: cliente for cliente in listar_clientes()}
    with st.sidebar:
        st.header("Pedido")
        if not clientes:
            st.error("No hay fichas de cliente válidas en data/clientes/.")
            return None, False

        id_cliente = st.selectbox("Cliente", list(clientes),
                                  format_func=lambda id_: clientes[id_].nombre,
                                  key="cliente")
        ficha_cliente(clientes[id_cliente])
        datos = {
            "cliente": id_cliente,
            "plataforma": st.selectbox("Plataforma", list(PLATAFORMAS), key="plataforma"),
            "audiencia": st.selectbox("Audiencia", list(AUDIENCIAS), key="audiencia"),
            "objetivo": st.selectbox("Objetivo", list(OBJETIVOS), key="objetivo"),
            "buscadores": st.checkbox("Optimización para buscadores", key="buscadores"),
            "tema": st.text_area("Tema", height=220, key="tema",
                                 placeholder="Qué hay que contar, con los datos que tengas."),
        }
        pulsado = st.button("Redactar", type="primary", width="stretch")
    return datos, pulsado


# --- Generación ---

def generar(datos):
    """Valida el pedido, lo redacta mostrando las etapas y guarda el resultado en la sesión."""
    pedido = Pedido(**datos)
    try:
        pedido.validar()
    except ValueError as error:
        st.sidebar.error(str(error))
        return

    with st.status(ETAPAS[REDACTANDO], expanded=True) as estado:
        def avisar(etapa):
            estado.update(label=ETAPAS[etapa])
            estado.write(ETAPAS[etapa])

        try:
            resultado = redactar(pedido, avisar=avisar)
        except Exception as error:
            estado.update(label="No se pudo redactar el texto", state="error")
            st.error(mensaje_error_redactor(error))
            return
        estado.update(label="Texto listo", state="complete", expanded=False)

    st.session_state["resultado"] = resultado
    st.session_state["plataforma_resultado"] = pedido.plataforma


# --- Resultado ---

def mostrar_texto(fragmento_html, plataforma):
    """Muestra el texto ya escapado: el blog con su Markdown, el resto en texto plano."""
    if plataforma == "Blog":
        # El $ se escapa para que Streamlit no lo lea como fórmula.
        st.markdown(fragmento_html.replace("$", "\\$"), unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="texto-plano">{html_en_linea(fragmento_html)}</div>',
                    unsafe_allow_html=True)


def notas_y_descarga(resultado, version, plataforma):
    """Notas debajo de una tarjeta y botón para descargar el texto plano."""
    notas = separar_notas(resultado.notas)
    st.markdown("**Datos que faltan**")
    if resultado.notas is None:
        texto_plano("El modelo no escribió notas.")
    else:
        texto_plano(notas.datos_que_faltan or "Sin indicar.")
        if notas.resto:
            texto_plano(notas.resto)
    with st.expander("A verificar"):
        texto_plano(notas.a_verificar or "Sin indicar.")
    with st.expander("Enfoque"):
        texto_plano(notas.enfoque or "Sin indicar.")

    extension = "md" if plataforma == "Blog" else "txt"
    st.download_button("Descargar el texto", resultado.texto,
                       file_name=f"texto_{version}.{extension}", mime="text/plain",
                       key=f"descargar_{version}", on_click="ignore")


def lista_problemas(problemas):
    """Lo que encontró la revisión, de lo más grave a lo más leve."""
    st.subheader("Lo que encontró la revisión")
    if not problemas:
        st.markdown("La revisión no encontró nada que señalar.")
        return

    elementos = []
    for problema in ordenar_problemas(problemas):
        fuerza = "suave" if problema.regla in TIPOS_LEVES else "fuerte"
        frase = (f'<div class="frase">“{html.escape(problema.frase)}”</div>'
                 if problema.frase else "")
        elementos.append(
            f'<li><span class="tipo {fuerza}">{html.escape(etiqueta(problema))}</span>'
            f"{frase}<div>{html.escape(problema.motivo)}</div></li>"
        )
    st.markdown(html_en_linea(f'<ul class="problemas">{"".join(elementos)}</ul>'),
                unsafe_allow_html=True)


def detalles_tecnicos(resultado):
    correccion = resultado.correccion
    lineas = [
        f"Redactor: {resultado.tokens_entrada} tokens de entrada y "
        f"{resultado.tokens_salida} de salida (incluye la reescritura).",
        f"Revisor: {resultado.tokens_revisor_entrada} tokens de entrada y "
        f"{resultado.tokens_revisor_salida} de salida (incluye la segunda revisión).",
        f"Intentos de redacción: {resultado.intentos}.",
        f"Señalamientos descartados por el filtro, versión original: {resultado.descartados}.",
    ]
    if correccion:
        lineas.append("Señalamientos descartados por el filtro, versión corregida: "
                      f"{correccion.descartados}.")
    with st.expander("Detalles técnicos"):
        texto_plano("\n".join(lineas))


def mostrar_resultado(resultado, plataforma):
    correccion = resultado.correccion
    for aviso in resultado.avisos + (correccion.avisos if correccion else []):
        st.warning(aviso)

    izquierda, derecha = st.columns(2, gap="medium")
    with izquierda:
        with st.container(border=True, key="tarjeta-original"):
            st.subheader("Versión original")
            mostrar_texto(resaltar(resultado.texto, resultado.problemas), plataforma)
        notas_y_descarga(resultado, "original", plataforma)
    with derecha:
        with st.container(border=True, key="tarjeta-corregida"):
            st.subheader("Versión corregida")
            if correccion:
                mostrar_texto(html.escape(correccion.texto, quote=False), plataforma)
            else:
                st.markdown("No hizo falta corregir.")
        if correccion:
            notas_y_descarga(correccion, "corregida", plataforma)

    lista_problemas(resultado.problemas)
    detalles_tecnicos(resultado)


# --- Página ---

st.set_page_config(page_title="La Redacción · Digital Content", page_icon=str(LOGO),
                   layout="wide")
poner_estilos()
cabecera()
datos, pulsado = formulario()
if pulsado:
    generar(datos)
if "resultado" in st.session_state:
    mostrar_resultado(st.session_state["resultado"], st.session_state["plataforma_resultado"])
