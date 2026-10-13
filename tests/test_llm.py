"""Pruebas de la creación de modelos, sin llamar a Groq."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.llm import obtener_revisor


def preparar_entorno(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("GROQ_MODEL_REVISOR", "qwen/qwen3.8-27b")


def test_revisor_sin_formato_no_lo_envia(monkeypatch):
    preparar_entorno(monkeypatch)
    revisor = obtener_revisor()
    assert revisor.reasoning_format is None
    assert revisor.reasoning_effort == "none"


def test_revisor_con_formato_parsed(monkeypatch):
    preparar_entorno(monkeypatch)
    revisor = obtener_revisor(razonamiento="low", max_tokens=2000,
                              formato_razonamiento="parsed")
    assert revisor.reasoning_format == "parsed"
    assert revisor.reasoning_effort == "low"
    assert revisor.max_tokens == 2000