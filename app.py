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
from redaccion.redactor import EMOJIS_TEXTO, TRATO_TEXTO  # noqa: E402

LOGO = RAIZ / "assets" / "logo.svg"
ESTILOS = RAIZ / "assets" / "estilos.css"


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


# --- Página ---

st.set_page_config(page_title="La Redacción · Digital Content", page_icon=str(LOGO),
                   layout="wide")
poner_estilos()
cabecera()
datos, pulsado = formulario()
