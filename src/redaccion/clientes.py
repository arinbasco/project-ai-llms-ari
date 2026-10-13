"""Fichas de cliente: carga desde data/clientes/ y validación."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

CARPETA_CLIENTES = Path(__file__).resolve().parents[2] / "data" / "clientes"

TIPOS = {"empresa", "persona"}
TRATOS = {"tu", "usted"}
EMOJIS = {"no", "moderado", "libre"}
FORMATO_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Voz:
    tono: list[str]
    trato: str
    expresiones_propias: list[str]
    expresiones_vetadas: list[str]
    emojis: str


@dataclass
class Cliente:
    id: str
    nombre: str
    tipo: str
    sector: str
    descripcion: str
    voz: Voz
    limites: list[str]

    def validar(self) -> None:
        """Lanza ValueError si la ficha no cumple las reglas."""
        if not FORMATO_ID.match(self.id):
            raise ValueError(f"Id de cliente no válido: '{self.id}'.")
        if not self.nombre.strip():
            raise ValueError(f"La ficha '{self.id}' no tiene nombre.")
        if self.voz.trato not in TRATOS:
            raise ValueError(
                f"La ficha '{self.id}' tiene un trato no válido: '{self.voz.trato}'."
            )
        if self.tipo and self.tipo not in TIPOS:
            raise ValueError(f"La ficha '{self.id}' tiene un tipo no válido: '{self.tipo}'.")
        if self.voz.emojis and self.voz.emojis not in EMOJIS:
            raise ValueError(
                f"La ficha '{self.id}' tiene un valor de emojis no válido: '{self.voz.emojis}'."
            )


def cargar_cliente(id_cliente: str) -> Cliente:
    """Lee data/clientes/<id_cliente>.json y devuelve la ficha validada."""
    if not FORMATO_ID.match(id_cliente):
        raise ValueError(f"Id de cliente no válido: '{id_cliente}'.")

    ruta = CARPETA_CLIENTES / f"{id_cliente}.json"
    if not ruta.exists():
        raise ValueError(f"No existe la ficha del cliente '{id_cliente}'.")

    with ruta.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)

    try:
        voz = Voz(**datos["voz"])
        cliente = Cliente(**{**datos, "voz": voz})
    except (KeyError, TypeError) as error:
        raise ValueError(
            f"La ficha '{id_cliente}' no tiene la forma esperada: {error}"
        ) from error

    if cliente.id != id_cliente:
        raise ValueError(
            f"El id de la ficha ('{cliente.id}') no coincide con el archivo ('{id_cliente}')."
        )

    cliente.validar()
    return cliente

def listar_clientes() -> list[Cliente]:
    """Devuelve las fichas válidas de data/clientes/, ordenadas por nombre.

    Las fichas que no cargan (JSON roto, campos que faltan, id que no
    coincide) se dejan fuera sin avisar.
    """
    validos = []
    for ruta in CARPETA_CLIENTES.glob("*.json"):
        try:
            validos.append(cargar_cliente(ruta.stem))
        except (ValueError, OSError):  # json.JSONDecodeError es un ValueError.
            continue
    return sorted(validos, key=lambda cliente: cliente.nombre.lower())
