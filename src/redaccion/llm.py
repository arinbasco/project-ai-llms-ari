import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def obtener_llm(temperatura=0.7, razonamiento="low", max_tokens=2000, semilla=42,
                modelo=None, formato_razonamiento=None):
    """Devuelve un modelo de Groq. Si no se indica uno, usa el del archivo .env.

    formato_razonamiento solo se envía si se indica, porque los modelos
    gpt-oss no lo admiten.
    """
    modelo = modelo or os.getenv("GROQ_MODEL")
    if not modelo:
        raise ValueError("Falta GROQ_MODEL en el archivo .env")

    opciones = {}
    if formato_razonamiento:
        opciones["reasoning_format"] = formato_razonamiento

    return ChatGroq(
        model=modelo,
        temperature=temperatura,
        reasoning_effort=razonamiento,
        max_tokens=max_tokens,
        model_kwargs={"seed": semilla},
        **opciones,
    )


def obtener_revisor(temperatura=0, razonamiento="none", max_tokens=1000,
                    formato_razonamiento=None):
    """Devuelve el modelo revisor de la capa 2, el de GROQ_MODEL_REVISOR del .env."""
    modelo = os.getenv("GROQ_MODEL_REVISOR")
    if not modelo:
        raise ValueError("Falta GROQ_MODEL_REVISOR en el archivo .env")
    return obtener_llm(
        temperatura=temperatura,
        razonamiento=razonamiento,
        max_tokens=max_tokens,
        modelo=modelo,
        formato_razonamiento=formato_razonamiento,
    )