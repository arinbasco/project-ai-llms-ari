import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def obtener_llm(temperatura=0.7, razonamiento="none", max_tokens=1000, semilla=42):
    """Devuelve el modelo de Groq configurado en el archivo .env."""
    modelo = os.getenv("GROQ_MODEL")
    if not modelo:
        raise ValueError("Falta GROQ_MODEL en el archivo .env")

    return ChatGroq(
        model=modelo,
        temperature=temperatura,
        reasoning_effort=razonamiento,
        max_tokens=max_tokens,
        model_kwargs={"seed": semilla},
    )