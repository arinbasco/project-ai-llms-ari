"""Pruebas del contador de pedidos diarios."""

import sys
import threading
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.limite import ContadorDiario

HOY = date(2026, 10, 13)
MANANA = date(2026, 10, 14)


def test_empieza_con_el_maximo():
    assert ContadorDiario(10).quedan("ari", HOY) == 10


def test_reservar_descuenta_hasta_el_maximo():
    contador = ContadorDiario(2)
    assert contador.reservar("ari", HOY)
    assert contador.reservar("ari", HOY)
    assert not contador.reservar("ari", HOY)
    assert contador.quedan("ari", HOY) == 0


def test_liberar_devuelve_el_pedido():
    contador = ContadorDiario(2)
    contador.reservar("ari", HOY)
    contador.liberar("ari", HOY)
    assert contador.quedan("ari", HOY) == 2


def test_liberar_sin_reservar_no_pasa_del_maximo():
    contador = ContadorDiario(2)
    contador.liberar("ari", HOY)
    assert contador.quedan("ari", HOY) == 2


def test_cada_usuario_tiene_su_cuenta():
    contador = ContadorDiario(1)
    contador.reservar("ari", HOY)
    assert contador.quedan("lucia", HOY) == 1


def test_al_dia_siguiente_vuelve_a_empezar():
    contador = ContadorDiario(1)
    contador.reservar("ari", HOY)
    assert contador.quedan("ari", MANANA) == 1
    assert contador.reservar("ari", MANANA)


def test_reservas_a_la_vez_no_pasan_del_maximo():
    contador = ContadorDiario(10)
    aceptadas = []

    def pedir():
        aceptadas.append(contador.reservar("ari", HOY))

    hilos = [threading.Thread(target=pedir) for _ in range(50)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert aceptadas.count(True) == 10
