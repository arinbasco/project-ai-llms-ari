"""Prueba rápida del redactor con un pedido real."""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.redactor import Pedido, redactar

pedido = Pedido(
    tema=(
        "Tostadero Ventura ofrece una merienda para niños y niñas: chocolate a la "
        "taza con churros por 3 euros, los sábados de 17:00 a 19:00. El chocolate "
        "se hace con cacao de Ecuador y leche entera, y hay opción con bebida de "
        "avena. Los sábados de noviembre, con la merienda hay un taller de dibujo "
        "gratuito de 17:30 a 18:30."
    ),
    plataforma="Instagram",
    audiencia="Infantil",
    objetivo="Vender",
)

resultado = redactar(pedido)
print(f"intentos {resultado.intentos} | entrada {resultado.tokens_entrada} "
      f"| salida {resultado.tokens_salida}")
print(f"avisos {resultado.avisos}\n")
print("TEXTO\n" + resultado.texto)
print("\nNOTAS\n" + str(resultado.notas))