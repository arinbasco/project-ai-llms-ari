"""Pruebas de la carga y validación de fichas de cliente."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion import clientes
from redaccion.clientes import cargar_cliente

FICHA_BASE = {
    "id": "cliente-prueba",
    "nombre": "Cliente de prueba",
    "tipo": "empresa",
    "sector": "",
    "descripcion": "",
    "voz": {"tono": [], "trato": "tu", "expresiones_propias": [],
            "expresiones_vetadas": [], "emojis": ""},
    "limites": [],
}


def ficha_con(**cambios):
    """Copia de FICHA_BASE con algunos campos cambiados."""
    datos = json.loads(json.dumps(FICHA_BASE))
    datos["voz"].update(cambios.pop("voz", {}))
    datos.update(cambios)
    return datos


def escribir_ficha(carpeta, datos):
    """Guarda la ficha como cliente-prueba.json en la carpeta indicada."""
    ruta = carpeta / "cliente-prueba.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize("id_cliente",
                         ["tostadero-ventura", "banco-faro", "universidad-munin"])
def test_las_fichas_de_la_demo_cargan(id_cliente):
    assert cargar_cliente(id_cliente).id == id_cliente


def test_ficha_con_campos_vacios_es_valida(tmp_path, monkeypatch):
    monkeypatch.setattr(clientes, "CARPETA_CLIENTES", tmp_path)
    escribir_ficha(tmp_path, FICHA_BASE)
    assert cargar_cliente("cliente-prueba").nombre == "Cliente de prueba"


FICHA_SIN_LIMITES = {k: v for k, v in FICHA_BASE.items() if k != "limites"}

FICHAS_INVALIDAS = [
    ficha_con(nombre="   "),
    ficha_con(voz={"trato": "vos"}),
    ficha_con(voz={"trato": ""}),
    ficha_con(tipo="cooperativa"),
    ficha_con(voz={"emojis": "muchos"}),
    ficha_con(id="otro-id"),
    ficha_con(tomo=["cercano"]),
    FICHA_SIN_LIMITES,
]


@pytest.mark.parametrize("datos", FICHAS_INVALIDAS)
def test_fichas_invalidas(datos, tmp_path, monkeypatch):
    monkeypatch.setattr(clientes, "CARPETA_CLIENTES", tmp_path)
    escribir_ficha(tmp_path, datos)
    with pytest.raises(ValueError):
        cargar_cliente("cliente-prueba")