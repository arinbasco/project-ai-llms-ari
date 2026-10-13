"""Pruebas de la carga y validación de fichas de cliente."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion import clientes
from redaccion.clientes import cargar_cliente, listar_clientes

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

def test_listar_clientes_de_la_demo():
    ids = [cliente.id for cliente in listar_clientes()]
    assert set(ids) == {"tostadero-ventura", "banco-faro", "universidad-munin"}


def test_listar_clientes_ordena_por_nombre_y_omite_los_invalidos(tmp_path, monkeypatch):
    monkeypatch.setattr(clientes, "CARPETA_CLIENTES", tmp_path)
    for id_cliente, nombre in [("zeta", "Zeta"), ("alfa", "alfa")]:
        datos = ficha_con(id=id_cliente, nombre=nombre)
        (tmp_path / f"{id_cliente}.json").write_text(json.dumps(datos), encoding="utf-8")
    (tmp_path / "roto.json").write_text("{no es json", encoding="utf-8")
    (tmp_path / "mal-id.json").write_text(json.dumps(ficha_con(id="otro")), encoding="utf-8")
    (tmp_path / "Mayusculas.json").write_text(json.dumps(FICHA_BASE), encoding="utf-8")
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")

    assert [cliente.nombre for cliente in listar_clientes()] == ["alfa", "Zeta"]


def test_listar_clientes_con_carpeta_vacia(tmp_path, monkeypatch):
    monkeypatch.setattr(clientes, "CARPETA_CLIENTES", tmp_path)
    assert listar_clientes() == []
