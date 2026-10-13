"""Prueba real del sistema completo: redactor, verificador y reescritura.

Por caso: redactor (una o dos llamadas), revisor, y si hay problemas
corregibles, reescritura y segunda revisión. Guarda el resultado en docs/
con fecha, modelos y configuración en la cabecera.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from redaccion.llm import obtener_llm, obtener_revisor
from redaccion.prompts import CORRECCION, REVISOR, SISTEMA
from redaccion.redactor import Pedido, redactar
from redaccion.verificador import TIPOS_CAPA2

SALIDA = RAIZ / "docs" / "prueba_verificador_04.txt"
PAUSA_SEGUNDOS = 90

CASOS = [
    ("Tostadero | Instagram | Vender", Pedido(
        tema=("Bolsa de café de Colombia recién tostado, 250 gramos, a 14 euros. "
              "Se compra en la cafetería."),
        plataforma="Instagram",
        audiencia="Público general",
        objetivo="Vender",
        cliente="tostadero-ventura",
    )),
    ("Banco Faro | LinkedIn | Informar", Pedido(
        tema=("Banco Faro añade a la app una herramienta para apartar los gastos "
              "fijos del mes en un espacio separado de la cuenta. Disponible desde "
              "el 1 de noviembre de 2026 para todos los clientes."),
        plataforma="LinkedIn",
        audiencia="Profesional",
        objetivo="Informar",
        cliente="banco-faro",
    )),
    ("Universidad Munin | Blog | Informar", Pedido(
        tema=("El grupo de Ecología Urbana de la Universidad Munin ha medido "
              "durante un año la temperatura en 40 calles de Madrid. En verano, "
              "las calles con árboles fueron de media 3 grados más frescas que las "
              "calles sin árboles. Los resultados se presentan en una conferencia "
              "abierta al público el 20 de noviembre de 2026 en el campus."),
        plataforma="Blog",
        audiencia="Divulgación",
        objetivo="Informar",
        cliente="universidad-munin",
    )),
]


def configuracion(llm):
    """Lee la configuración real del modelo, sin escribirla a mano."""
    campos = ["model_name", "temperature", "reasoning_effort", "max_tokens",
              "model_kwargs"]
    return " | ".join(f"{campo}={getattr(llm, campo, 'no consta')}"
                      for campo in campos)


def bloque_version(titulo, version):
    """Texto, notas, avisos y problemas de una versión (original o corregida)."""
    capa1 = [p for p in version.problemas if p.regla not in TIPOS_CAPA2]
    capa2 = [p for p in version.problemas if p.regla in TIPOS_CAPA2]
    lineas = [
        titulo,
        "",
        "TEXTO",
        version.texto,
        "",
        "NOTAS",
        version.notas or "(sin notas)",
        "",
        f"Avisos: {version.avisos or 'ninguno'}",
        "",
        f"CAPA 1: {len(capa1)} problemas",
    ]
    lineas += [f"- [{p.regla}] {p.motivo} | frase: {p.frase}"
               for p in capa1] or ["- ninguno"]
    lineas += [
        "",
        f"CAPA 2: {len(capa2)} problemas | descartados por el filtro: {version.descartados}",
    ]
    lineas += [f"- [{p.regla}] {p.frase} | {p.motivo}"
               for p in capa2] or ["- ninguno"]
    return lineas


def main():
    if SALIDA.exists():
        sys.exit(f"{SALIDA.name} ya existe. Cambia SALIDA para no sobrescribirlo.")

    llm = obtener_llm()
    revisor = obtener_revisor()
    lineas = [
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"Redactor: {configuracion(llm)}",
        f"Revisor: {configuracion(revisor)}",
        (f"SISTEMA: {len(SISTEMA)} caracteres | REVISOR: {len(REVISOR)} caracteres | "
         f"CORRECCION: {len(CORRECCION)} caracteres"),
        "Reescritura: activada",
        f"Script: scripts/{Path(__file__).name}",
        "",
    ]

    for numero, (nombre, pedido) in enumerate(CASOS, start=1):
        if numero > 1:
            print(f"Esperando {PAUSA_SEGUNDOS} segundos...")
            time.sleep(PAUSA_SEGUNDOS)
        print(f"Caso {numero}: {nombre}")

        resultado = redactar(pedido, llm, revisor=revisor)

        lineas += [
            "=" * 70,
            f"CASO {numero}. {nombre}",
            f"Cliente: {pedido.cliente} | Audiencia: {pedido.audiencia}",
            f"Pedido: {pedido.tema}",
            f"Intentos: {resultado.intentos}",
            (f"Tokens del redactor (con reescritura): entrada {resultado.tokens_entrada} | "
             f"salida {resultado.tokens_salida}"),
            (f"Tokens del revisor (con segunda revisión): entrada "
             f"{resultado.tokens_revisor_entrada} | salida {resultado.tokens_revisor_salida}"),
            "",
        ]
        lineas += bloque_version("--- VERSIÓN ORIGINAL ---", resultado)
        lineas.append("")
        if resultado.correccion:
            lineas += bloque_version("--- VERSIÓN CORREGIDA ---", resultado.correccion)
        else:
            lineas += ["--- VERSIÓN CORREGIDA ---", "(no hizo falta reescribir)"]
        lineas.append("")

        SALIDA.write_text("\n".join(lineas), encoding="utf-8")

    print(f"Guardado en {SALIDA}")


if __name__ == "__main__":
    main()