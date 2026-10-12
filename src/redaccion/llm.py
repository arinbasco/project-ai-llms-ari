import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def obtener_llm(temperatura=0.7, razonamiento="low", max_tokens=2000, semilla=42, modelo=None):
    """Devuelve un modelo de Groq. Si no se indica uno, usa el del archivo .env."""
    modelo = modelo or os.getenv("GROQ_MODEL")
    if not modelo:
        raise ValueError("Falta GROQ_MODEL en el archivo .env")

    return ChatGroq(
        model=modelo,
        temperature=temperatura,
        reasoning_effort=razonamiento,
        max_tokens=max_tokens,
        model_kwargs={"seed": semilla},
    )