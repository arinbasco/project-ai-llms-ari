"""Mide tokens y revisa textos con pedidos completos, como los de una agencia."""

import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.messages import HumanMessage, SystemMessage

from redaccion.llm import obtener_llm
from redaccion.prompts import (
    AJUSTES_INFANTIL,
    AUDIENCIAS,
    BUSCADORES,
    OBJETIVOS,
    OBJETIVOS_PLATAFORMA,
    PLATAFORMAS,
    SISTEMA,
    USUARIO,
)

MODELO = "openai/gpt-oss-120b"
RAZONAMIENTO = "low"

CASOS = [
    {
        "nombre": "Hilo narrativo de cafetería",
        "tema": (
            "Tostadero Ventura, cafetería de especialidad en Chamberí (Madrid), lanza "
            "un café de Colombia de la finca La Esperanza, en Huila, que cultiva la "
            "familia Rojas. Lucía, la tostadora de la cafetería, viajó a la finca en "
            "marzo de 2026 y eligió este lote entre doce muestras. Notas de cata: "
            "panela, mandarina y cacao. Proceso lavado. Precio: 3,20 euros el café de "
            "filtro y 14 euros la bolsa de 250 gramos. Disponible desde el 20 de "
            "octubre de 2026. Horario: de lunes a sábado, de 8:00 a 20:00."
        ),
        "plataforma": "X",
        "audiencia": "Público general",
        "objetivo": "Contar una historia",
        "buscadores": False,
    },
    {
        "nombre": "Jornada de puertas abiertas",
        "tema": (
            "La Universidad del Prado organiza una jornada de puertas abiertas del "
            "grado en Periodismo el sábado 14 de noviembre de 2026, de 10:00 a 14:00, "
            "en la Facultad de Comunicación del campus de Moncloa. Programa: a las "
            "10:00, bienvenida de la decana, Marta Ibáñez. A las 10:30, charla sobre "
            "las prácticas en medios. A las 11:30, visita al plató de televisión y a "
            "la radio de la facultad. A las 12:30, preguntas a estudiantes de cuarto "
            "curso. Dirigida a estudiantes de bachillerato y a sus familias. "
            "Inscripción gratuita en la web de la universidad, sección Jornadas, "
            "hasta el 10 de noviembre. Hay 120 plazas. El edificio es accesible en "
            "silla de ruedas."
        ),
        "plataforma": "Blog",
        "audiencia": "Institucional",
        "objetivo": "Convocar",
        "buscadores": True,
    },
    {
        "nombre": "Merienda infantil",
        "tema": (
            "Tostadero Ventura ofrece una merienda para niños y niñas: chocolate a la "
            "taza con churros por 3 euros, los sábados de 17:00 a 19:00. El chocolate "
            "se hace con cacao de Ecuador y leche entera, y hay opción con bebida de "
            "avena. Los sábados de noviembre, con la merienda hay un taller de dibujo "
            "gratuito de 17:30 a 18:30."
        ),
        "plataforma": "Instagram",
        "audiencia": "Infantil",
        "objetivo": "Vender",
        "buscadores": False,
    },
]


def armar_pedido(caso):
    """Rellena la plantilla USUARIO con los bloques que corresponden al caso."""
    extras = []
    if caso["audiencia"] == "Infantil" and caso["objetivo"] in AJUSTES_INFANTIL:
        extras.append(AJUSTES_INFANTIL[caso["objetivo"]])
    if caso["buscadores"]:
        extras.append(BUSCADORES)
    return USUARIO.format(
        tema=caso["tema"],
        plataforma=PLATAFORMAS[caso["plataforma"]],
        audiencia=AUDIENCIAS[caso["audiencia"]],
        objetivo=OBJETIVOS[caso["objetivo"]],
        objetivo_plataforma=OBJETIVOS_PLATAFORMA[caso["objetivo"]][caso["plataforma"]],
        extras="\n".join(extras),
    )


llm = obtener_llm(modelo=MODELO, razonamiento=RAZONAMIENTO)
print(f"Comparación de modelo | {MODELO} | razonamiento {RAZONAMIENTO} | temperatura 0.7 | semilla 42 | techo 2000\n")

for numero, caso in enumerate(CASOS, start=1):
    pedido = armar_pedido(caso)
    mensajes = [SystemMessage(content=SISTEMA), HumanMessage(content=pedido)]

    inicio = time.perf_counter()
    respuesta = llm.invoke(mensajes)
    segundos = time.perf_counter() - inicio

    uso = respuesta.usage_metadata
    motivo = respuesta.response_metadata.get("finish_reason", "desconocido")
    texto = respuesta.content.split("NOTAS PARA REVISAR")[0]
    tiene_notas = "NOTAS PARA REVISAR" in respuesta.content

    print("=" * 70)
    print(f"{numero}. {caso['nombre']} | {caso['plataforma']} | {caso['audiencia']} "
          f"| {caso['objetivo']} | buscadores {caso['buscadores']}")
    print(f"caracteres sistema {len(SISTEMA)} | caracteres pedido {len(pedido)}")
    print(f"tokens entrada {uso['input_tokens']} | salida {uso['output_tokens']} "
          f"| total {uso['total_tokens']}")
    print(f"palabras del texto {len(texto.split())} | notas {tiene_notas} "
          f"| motivo de cierre {motivo} | tiempo {segundos:.1f} s")
    print("-" * 70)
    print(respuesta.content)
    print()
    time.sleep(60)