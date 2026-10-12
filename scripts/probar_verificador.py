"""Prueba real del redactor con ficha y de la capa 1 del verificador.

Hace una llamada a Groq por caso (dos si hay reintento) y guarda el
resultado en docs/ con fecha, modelo y configuración en la cabecera.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from redaccion.clientes import cargar_cliente
from redaccion.llm import obtener_llm
from redaccion.prompts import SISTEMA
from redaccion.redactor import Pedido, redactar
from redaccion.verificador import verificar_capa1

SALIDA = RAIZ / "docs" / "prueba_verificador_01.txt"
PAUSA_SEGUNDOS = 30

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


def main():
    if SALIDA.exists():
        sys.exit(f"{SALIDA.name} ya existe. Cambia SALIDA para no sobrescribirlo.")

    llm = obtener_llm()
    lineas = [
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"Configuración: {configuracion(llm)}",
        f"SISTEMA: {len(SISTEMA)} caracteres",
        f"Script: scripts/{Path(__file__).name}",
        "",
    ]

    for numero, (nombre, pedido) in enumerate(CASOS, start=1):
        if numero > 1:
            print(f"Esperando {PAUSA_SEGUNDOS} segundos...")
            time.sleep(PAUSA_SEGUNDOS)
        print(f"Caso {numero}: {nombre}")

        resultado = redactar(pedido, llm)
        cliente = cargar_cliente(pedido.cliente)
        problemas = verificar_capa1(resultado.texto, resultado.notas, pedido, cliente)

        lineas += [
            "=" * 70,
            f"CASO {numero}. {nombre}",
            f"Cliente: {pedido.cliente} | Audiencia: {pedido.audiencia}",
            f"Pedido: {pedido.tema}",
            (f"Intentos: {resultado.intentos} | Tokens de entrada: "
             f"{resultado.tokens_entrada} | Tokens de salida: {resultado.tokens_salida}"),
            f"Avisos del redactor: {resultado.avisos or 'ninguno'}",
            "",
            "TEXTO",
            resultado.texto,
            "",
            "NOTAS",
            resultado.notas or "(sin notas)",
            "",
            f"CAPA 1: {len(problemas)} problemas",
        ]
        lineas += [f"- [{p.regla}] {p.motivo} | frase: {p.frase}"
                   for p in problemas] or ["- ninguno"]
        lineas.append("")

        SALIDA.write_text("\n".join(lineas), encoding="utf-8")

    print(f"Guardado en {SALIDA}")


if __name__ == "__main__":
    main()