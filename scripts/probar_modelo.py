import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from redaccion.llm import obtener_llm

PEDIDO = (
    "Escribí un post de Instagram para una cafetería de Madrid que lanza "
    "un café de especialidad de Colombia. Tono cercano, entre 80 y 120 palabras, "
    "con un llamado a la acción y cinco hashtags."
)

CONFIGURACIONES = [
    {"temperatura": 0.7, "razonamiento": "none"},
    {"temperatura": 0.7, "razonamiento": "low"},
    {"temperatura": 0.7, "razonamiento": "medium"},
    {"temperatura": 0.3, "razonamiento": "none"},
    {"temperatura": 0.9, "razonamiento": "none"},
]

print("Modelo y parámetros fijos de esta prueba")
print("semilla 42 | techo 1000 tokens\n")

for numero, config in enumerate(CONFIGURACIONES, start=1):
    llm = obtener_llm(**config)

    inicio = time.perf_counter()
    respuesta = llm.invoke(PEDIDO)
    segundos = time.perf_counter() - inicio

    uso = respuesta.usage_metadata
    print("=" * 70)
    print(f"PRUEBA {numero} | temperatura {config['temperatura']} | razonamiento {config['razonamiento']}")
    print(f"tokens entrada {uso['input_tokens']} | salida {uso['output_tokens']} | tiempo {segundos:.1f} s")
    print("-" * 70)
    print(respuesta.content)
    print()

    time.sleep(20)