"""Vuelve a revisar con la capa 2 los textos de una prueba ya guardada.

Sirve para comparar configuraciones del revisor con los mismos textos,
porque con gpt-oss los textos cambian en cada ejecución. La configuración
de cada pasada se cambia en las constantes de abajo.
"""

import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from probar_verificador import CASOS, configuracion
from redaccion.clientes import cargar_cliente
from redaccion.llm import obtener_revisor
from redaccion.prompts import REVISOR
from redaccion.verificador import verificar_capa2

# --- Configuración de esta pasada ---
RAZONAMIENTO = "low"
TEMPERATURA = 0
MAX_TOKENS = 2000
FORMATO_RAZONAMIENTO = "parsed"
SALIDA = RAIZ / "docs" / "prueba_revisor_04.txt"
# -------------------------------------

ENTRADA = RAIZ / "docs" / "prueba_verificador_02.txt"
PAUSA_SEGUNDOS = 20


def leer_textos(ruta):
    """Saca de un informe de prueba el texto de cada caso, en orden."""
    contenido = ruta.read_text(encoding="utf-8")
    textos = []
    for bloque in contenido.split("=" * 70)[1:]:
        inicio = bloque.index("TEXTO\n") + len("TEXTO\n")
        fin = bloque.index("\n\nNOTAS\n", inicio)
        textos.append(bloque[inicio:fin].strip())
    return textos


def main():
    if SALIDA.exists():
        sys.exit(f"{SALIDA.name} ya existe. Cambia SALIDA para no sobrescribirlo.")

    textos = leer_textos(ENTRADA)
    revisor = obtener_revisor(
        temperatura=TEMPERATURA,
        razonamiento=RAZONAMIENTO,
        max_tokens=MAX_TOKENS,
        formato_razonamiento=FORMATO_RAZONAMIENTO,
    )
    lineas = [
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M}",
        f"Revisor: {configuracion(revisor)} | reasoning_format={revisor.reasoning_format}",
        f"REVISOR: {len(REVISOR)} caracteres",
        f"Textos de: docs/{ENTRADA.name}",
        f"Script: scripts/{Path(__file__).name}",
        "",
    ]

    for numero, ((nombre, pedido), texto) in enumerate(zip(CASOS, textos), start=1):
        if numero > 1:
            print(f"Esperando {PAUSA_SEGUNDOS} segundos...")
            time.sleep(PAUSA_SEGUNDOS)
        print(f"Caso {numero}: {nombre}")

        revision = verificar_capa2(texto, pedido, cargar_cliente(pedido.cliente), revisor)
        posible_corte = revision.tokens_salida >= MAX_TOKENS - 10

        lineas += [
            "=" * 70,
            f"CASO {numero}. {nombre}",
            f"Pedido: {pedido.tema}",
            "",
            "TEXTO",
            texto,
            "",
            (f"Tokens del revisor: entrada {revision.tokens_entrada} | "
             f"salida {revision.tokens_salida}"
             + (" | POSIBLE CORTE POR LÍMITE DE TOKENS" if posible_corte else "")),
            "",
            "RAZONAMIENTO DEL REVISOR",
            revision.razonamiento or "(vacío)",
            "",
            (f"CAPA 2: {len(revision.problemas)} problemas | descartados por el "
             f"filtro: {revision.descartados}"),
        ]
        lineas += [f"- [{p.regla}] {p.frase} | {p.motivo}"
                   for p in revision.problemas] or ["- ninguno"]
        lineas.append("")

        SALIDA.write_text("\n".join(lineas), encoding="utf-8")

    print(f"Guardado en {SALIDA}")


if __name__ == "__main__":
    main()