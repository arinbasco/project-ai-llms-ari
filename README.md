# La Redacción

Generador de contenido con modelos de lenguaje para Digital Content, una agencia ficticia que publica en redes sociales y blogs para sus clientes. A partir de un pedido, el sistema redacta un texto listo para publicar, revisa qué afirma más allá de los datos recibidos y propone una versión corregida.

Proyecto individual del Bootcamp de Inteligencia Artificial de Factoría F5 en Madrid (promoción P7), basado en el [briefing del proyecto LLMs](https://github.com/Factoria-F5-madrid/project-ai-llms).

Demo desplegada en [Streamlit Community Cloud](https://redacciondigitalcontent.streamlit.app/).

## Índice

1. [Qué hace](#qué-hace)
2. [Cómo funciona](#cómo-funciona)
3. [La interfaz](#la-interfaz)
4. [Decisiones y su porqué](#decisiones-y-su-porqué)
5. [Lo que mostraron las pruebas](#lo-que-mostraron-las-pruebas)
6. [Puesta en marcha en local](#puesta-en-marcha-en-local)
7. [Docker](#docker)
8. [Despliegue](#despliegue)
9. [Estructura del repositorio](#estructura-del-repositorio)
10. [Limitaciones](#limitaciones)
11. [Trabajo futuro](#trabajo-futuro)
12. [Relación con el briefing](#relación-con-el-briefing)
13. [Referencias](#referencias)

## Qué hace

Una persona de la agencia elige un cliente, una plataforma, una audiencia y un objetivo, y escribe el tema del encargo con los datos que tiene. El sistema devuelve tres cosas.

* El texto redactado, con la voz del cliente y el formato de la plataforma.
* Una revisión que señala las frases que contradicen el pedido, las que añaden datos que nadie dio y las que son solo estilo.
* Una versión corregida, cuando hay algo que corregir, con su propia revisión.

| Opción | Valores |
|---|---|
| Plataforma | X, Instagram, LinkedIn, Blog |
| Audiencia | Público general, Infantil (8 a 12 años), Profesional, Divulgación, Institucional |
| Objetivo | Informar, Vender, Contar una historia, Generar conversación, Resolver un problema, Convocar |
| Extra | Optimización para buscadores |

La demo incluye tres clientes ficticios. Tostadero Ventura es una cafetería de barrio que tuesta su propio café. Banco Faro es un banco que funciona solo desde su app. La Universidad Munin es una universidad con campus en Madrid.

## Cómo funciona

El sistema es un *workflow*, una cadena de pasos fijos que decide el código, con dos modelos de lenguaje en puntos concretos. Los modelos escriben o revisan cuando les toca, sin elegir qué paso viene después. Por eso no se describe como un sistema de agentes.

```
pedido → validar → cargar ficha → armar el prompt → redactar
       → capa 1 (reglas en código)
       → capa 2 (un segundo modelo revisa)
       → capa 3 (reescritura, si hay algo corregible)
       → resultado con las dos versiones y sus revisiones
```

### El redactor

Usa `openai/gpt-oss-120b` en Groq a través de LangChain. El prompt se arma por bloques en `src/redaccion/prompts.py`.

* Un mensaje de sistema con las normas comunes (español de España, no inventar datos, estilo y formato de la respuesta).
* Un mensaje de usuario con la ficha del cliente, el tema y los bloques de plataforma, audiencia y objetivo.

El modelo entrega el texto y unas notas para revisar con tres apartados (datos que faltan, a verificar y enfoque). Si las notas no llegan o el texto se corta, el redactor repite la llamada una vez.

### La ficha de cliente

Cada cliente es un JSON en `data/clientes/` con su identidad, su voz (tono, trato de tú o de usted, expresiones propias y vetadas, uso de emojis) y sus límites. La ficha entra en el mensaje de usuario y decide el trato del texto. Todo el código obtiene las fichas a través de `cargar_cliente()`, así que el día que pasen a una base de datos solo cambia esa función.

### El verificador

Funciona como un guardarraíl de salida. Revisa lo que escribió el modelo y entrega el texto con los problemas señalados, sin bloquearlo.

**Capa 1, reglas en código.** No gasta cuota y da siempre el mismo resultado. Comprueba ocho reglas.

* Expresiones vetadas por la ficha.
* Markdown fuera del blog.
* Número de hashtags según la plataforma y la audiencia.
* Emojis cuando la ficha, la plataforma o la audiencia no los permiten.
* Longitud de los posts de X y hashtags solo en el último post del hilo.
* Frases que los prompts piden evitar, salvo si vienen en el pedido.
* Trato contrario al de la ficha, detectado por los pronombres.
* Notas completas y en texto plano.

**Capa 2, un modelo que revisa a otro.** `qwen/qwen3.8-27b` recibe la ficha, el pedido y el texto, y devuelve una lista de frases con su tipo y su motivo.

| Tipo | Qué señala |
|---|---|
| CONTRADICE | Afirmaciones que contradicen, deforman o exageran el pedido o la ficha |
| AÑADE | Afirmaciones comprobables que no salen del pedido ni de la ficha |
| GENERAL | Conocimiento general que no está en el pedido ni atribuye nada al cliente |
| ADORNO | Adjetivos, imágenes y frases de estilo sin ningún dato |

CONTRADICE y AÑADE siguen la distinción entre alucinación intrínseca y extrínseca de Ji et al. (2023). GENERAL y ADORNO responden a un criterio propio, para separar lo leve de lo grave.

Un filtro de citas comprueba en código que cada frase señalada aparece de verdad en el texto. Si el revisor cita algo que no existe, el aviso se descarta. Si la llamada al revisor falla, el texto se entrega igual, con un aviso.

### Capa 3, la reescritura

Si la revisión encuentra problemas de la capa 1 o de los tipos CONTRADICE y AÑADE, el redactor recibe su propio texto y la lista de problemas, y escribe una versión corregida. Las instrucciones le piden quitar lo que no tiene respaldo sin sustituirlo por otra cosa, dejar intactas las frases no señaladas y anotar en las notas los datos que harían falta. La versión corregida vuelve a pasar por las capas 1 y 2. GENERAL y ADORNO se muestran, pero no se corrigen.

Hay una sola ronda de corrección. Si la reescritura falla, se entrega el original con un aviso.

## La interfaz

La interfaz está hecha con Streamlit y requiere iniciar sesión con usuario y contraseña (`streamlit-authenticator`).

* **Barra lateral.** Desplegables de cliente, plataforma, audiencia y objetivo, la casilla de buscadores y el tema como único campo de texto libre. Debajo del cliente se puede abrir el resumen de su ficha. Los valores se conservan después de generar, para completar el pedido y volver a enviarlo.
* **Progreso por etapas.** Redactando, revisando, corrigiendo y revisando la corrección. Las etapas que no ocurren no aparecen.
* **Dos tarjetas lado a lado.** A la izquierda, la versión original con las frases señaladas resaltadas en dorado (graves) o en rosa (leves). A la derecha, la versión corregida o el aviso de que no hizo falta corregir. Debajo de cada una, los datos que faltan a la vista, las otras notas plegadas y un botón para descargar el texto.
* **Lo que encontró la revisión.** La lista de problemas de la versión original, de lo más grave a lo más leve.
* **Detalles técnicos.** Plegados al final, con los tokens de cada modelo, los intentos y los avisos descartados por el filtro.
* **Límite diario.** Diez pedidos por usuario y día. Un pedido no cuenta si el redactor falla.

El diseño usa una paleta de cinco colores (`#3A0D2C`, `#6A1B4D`, `#D9B1C7`, `#F3E6EF` y `#C6A24B`). Las combinaciones de texto y fondo que usa la interfaz cumplen el nivel AA de contraste de las pautas WCAG para texto normal. El logo es un monograma DC propio en SVG.

## Decisiones y su porqué

| Decisión | Motivo |
|---|---|
| Redactor `gpt-oss-120b` con razonamiento bajo, temperatura 0,7 y techo de 2.000 tokens | Al comparar con `qwen3.8-27b` sobre los mismos pedidos, escribió mejor, mantuvo el trato y entregó siempre las notas |
| Revisor de otra familia de modelos | Los modelos que evalúan textos tienden a favorecer los suyos (Zheng et al., 2023; Panickssery et al., 2024). Un revisor de la misma familia podría pasar por alto los inventos de su redactor |
| Revisor sin razonamiento y con temperatura 0 | Con razonamiento, Qwen juzgaba mejor, pero agotaba el límite de 1.000 tokens de salida por minuto del plan gratuito antes de terminar la respuesta |
| La reescritura la hace el redactor | Conserva la voz de la ficha. El revisor solo señala |
| GENERAL y ADORNO no se corrigen | Son visibles para quien revisa, pero no son errores de datos |
| Groq en plan gratuito | El briefing pide minimizar el gasto mientras el sistema es una prueba de concepto |
| Sin base de datos | Con el alcance actual no hace falta. Ver [Limitaciones](#limitaciones) |


## Lo que mostraron las pruebas

Las pruebas con llamadas reales están guardadas en `docs/`, con la fecha, los modelos y la configuración en la cabecera de cada archivo. Son pocos casos y ninguna constituye una evaluación sistemática, así que lo que sigue son observaciones.

* **Las notas del propio redactor no detectan sus inventos.** En varios casos indicaban que no faltaba ningún dato mientras el texto afirmaba cosas como "100 % colombiano" o "de forma automática" sin que el pedido lo dijera.
* **La capa 2 detecta inventos que la capa 1 no puede ver,** como funciones de un producto, metodologías de un estudio o canales de contacto que nadie dio. También encontró una contradicción de fechas, un "disponible de inmediato" frente a un pedido que daba una fecha futura.
* **El revisor no es del todo estable.** Entre una pasada y otra cambia algún tipo o señala frases que antes había dejado pasar.
* **Las llamadas a la acción con destinos inventados** ("consulte la sección de novedades") se escaparon a la revisión en varias pruebas, probablemente porque el prompt del revisor excluye las llamadas a la acción genéricas.
* **La reescritura funcionó mejor en textos cortos.** En Instagram quitó lo señalado y el post quedó listo. En LinkedIn y en el blog, quitar los inventos dejó textos cortos o con huecos. En esos casos tiene más sentido completar el pedido con datos reales y volver a generarlo, y la nota de datos que faltan indica qué pedirle al cliente.
* **Con la optimización para buscadores, un texto salió con menos relleno.** Una explicación posible es que ese bloque pide evitar frases que no aportan información. Con una sola prueba no se puede descartar el efecto del azar.
* **Coste.** Cada pedido gastó entre 6.600 y 10.100 tokens, sumando los dos modelos y todas las llamadas (redactar, revisar, corregir y volver a revisar).

## Puesta en marcha en local

Requisitos. Python 3.13 y una clave de API de Groq.

Los comandos están escritos para Git Bash en Windows. En macOS o Linux cambia solo la ruta de activación del entorno.

**Clonar el repositorio y crear el entorno**

```bash
git clone <url-del-repositorio>
cd project-ai-llms-ari
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

* `git clone` descarga el repositorio y `cd` entra en su carpeta.
* `python -m venv .venv` crea un entorno virtual en la carpeta `.venv`.
* `source .venv/Scripts/activate` lo activa. En macOS o Linux la ruta es `.venv/bin/activate`.
* `pip install -r requirements.txt` instala las versiones fijadas en el archivo.

**Preparar los secretos**

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

* `cp` copia la plantilla con el nombre que busca Streamlit. El archivo copiado está en `.gitignore` y no se sube nunca.

En `.streamlit/secrets.toml` van las claves de Groq (`GROQ_API_KEY`, `GROQ_MODEL` y `GROQ_MODEL_REVISOR`) arriba del todo, una cookie con su clave aleatoria y un bloque por usuario. En TOML los textos van entre comillas.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

* Genera una cadena aleatoria para el campo `key` de la cookie.

```bash
python scripts/cifrar_contrasena.py
```

* Pide la contraseña dos veces sin mostrarla y devuelve la línea `password` cifrada para el bloque del usuario. La contraseña original no se guarda en ningún sitio.

El usuario con el que se entra es el nombre del bloque `[credentials.usernames.<usuario>]`.

**Arrancar la app**

```bash
streamlit run app.py
```

* Arranca la interfaz en `http://localhost:8501`. Si se edita `secrets.toml`, hay que pararla con Ctrl+C y volver a lanzarla.

**Ejecutar los tests**

```bash
GROQ_API_KEY= python -m pytest -v
```

* `GROQ_API_KEY=` deja la clave vacía solo para este comando, como garantía de que ningún test llama a Groq.
* `python -m pytest -v` ejecuta los 113 tests, uno por línea. Todos usan modelos falsos.

Los scripts de `scripts/` hacen llamadas reales a Groq y leen la configuración de un archivo `.env` (ver `.env.example`).

## Docker

```bash
docker build -t la-redaccion .
```

* `docker build` construye la imagen siguiendo el `Dockerfile`, y `-t la-redaccion` le pone nombre. El punto final indica la carpeta actual. Lo que aparece en `.dockerignore`, incluidos los secretos, se queda fuera de la imagen.

```bash
docker run --rm -p 8501:8501 -v "$(pwd)/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro" la-redaccion
```

* `--rm` borra el contenedor al pararlo.
* `-p 8501:8501` conecta el puerto 8501 del ordenador con el del contenedor.
* `-v` monta el archivo de secretos dentro del contenedor, y `:ro` lo deja en solo lectura. Los secretos nunca forman parte de la imagen.

La imagen usa Python 3.13, se ejecuta con un usuario sin privilegios e incluye una comprobación de salud de Streamlit.

## Despliegue

La app se despliega en Streamlit Community Cloud desde la rama `main`, con `app.py` como punto de entrada.

1. Crear la app desde el repositorio en Community Cloud.
2. En "Advanced settings", elegir Python 3.13. Community Cloud usa la 3.12 por defecto.
3. Pegar el contenido de `.streamlit/secrets.toml` en el campo "Secrets".

Community Cloud duerme las apps que pasan 12 horas sin tráfico y no garantiza que se conserven los archivos que escribe la app.

## Estructura del repositorio

```
app.py                     interfaz de Streamlit
assets/                    logo y estilos
data/clientes/             fichas de los clientes en JSON
docs/                      pruebas reales guardadas y documentos del proyecto
scripts/                   scripts que se lanzan a mano (pruebas reales y cifrado)
src/redaccion/
    llm.py                 creación del redactor y del revisor
    prompts.py             todos los textos que reciben los modelos
    clientes.py            carga, validación y listado de fichas
    verificador.py         capas 1 y 2
    redactor.py            pedido, resultado, redacción y capa 3
    presentacion.py        funciones para la interfaz (notas, orden, resaltado)
    limite.py              límite de pedidos por usuario y día
tests/                     113 tests con modelos falsos
Dockerfile
.streamlit/config.toml     tema de la interfaz
.streamlit/secrets.example.toml   plantilla de los secretos
```

## Limitaciones

* **Sin persistencia.** No se guarda el historial de pedidos y los clientes solo se crean añadiendo un JSON al repositorio.
* **El contador diario vive en memoria.** Se pone a cero si la app se reinicia, y en Community Cloud eso pasa al desplegar, al cambiar los secretos o cuando la app se duerme. Además usa la fecha del servidor, que en la nube suele ser UTC.
* **Sin evaluación sistemática.** Las observaciones sobre el verificador y la reescritura salen de pocos casos. Los textos de las pruebas sirvieron para ajustar los prompts, así que tampoco valdrían como conjunto de prueba independiente.
* **Variabilidad.** Con `gpt-oss` la semilla no reproduce resultados, y el revisor también varía entre pasadas.
* **Revisor sin razonamiento.** Es la configuración que cabe en el plan gratuito, aunque con razonamiento juzgaba mejor.
* **Dos fuentes de configuración en local.** La app lee `secrets.toml` y los scripts leen `.env`. Si falta una clave en `secrets.toml`, la app puede tomar la del `.env` sin avisar.
* **Contraste de los textos atenuados.** Streamlit muestra algunos textos secundarios con menos opacidad. Su contraste no se ha medido en el navegador.
* **Docker.** La imagen está preparada, pero queda pendiente probarla de principio a fin.
* **`app.py` no tiene tests automáticos.**

## Trabajo futuro

* Una base de datos externa para el historial, los clientes y el contador.
* Trazabilidad de las llamadas con LangSmith.
* Una evaluación sistemática del verificador con textos nuevos anotados a mano, midiendo precisión y exhaustividad por tipo de problema.
* Un RAG de divulgación científica con artículos de arXiv, para que las explicaciones generales tengan fuente.
* Un revisor con razonamiento, con más cuota o con otro proveedor.
* Contenido en inglés, francés e italiano.
* Selector de modelo para el redactor.

## Relación con el briefing

| Nivel | Hecho | Pendiente |
|---|---|---|
| Esencial | Texto según tema, plataforma y audiencia. Interfaz web. Repositorio con commits descriptivos. README | Artículo en Medium |
| Medio | Docker. Información de la empresa que publica (la ficha de cliente) | Selector de al menos dos LLMs. Imágenes |
| Avanzado | | Trazabilidad. Idiomas. Noticias financieras. RAG científico |
| Experto | Guardarraíles contra alucinaciones (el verificador de tres capas) | Sistema multiagente. Graph RAG |

## Referencias

* Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y., Madotto, A. y Fung, P. (2023). Survey of Hallucination in Natural Language Generation. *ACM Computing Surveys*, 55(12), 248. [arXiv 2202.03629](https://arxiv.org/abs/2202.03629)
* Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E. y Stoica, I. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. *NeurIPS 2023, Datasets and Benchmarks Track*. [arXiv 2306.05685](https://arxiv.org/abs/2306.05685)
* Panickssery, A., Bowman, S. R. y Feng, S. (2024). LLM Evaluators Recognize and Favor Their Own Generations. *NeurIPS 2024*. [arXiv 2404.13076](https://arxiv.org/abs/2404.13076)
* Groq. [Rate Limits](https://console.groq.com/docs/rate-limits) y [Reasoning](https://console.groq.com/docs/reasoning).
* Streamlit. [Secrets management](https://docs.streamlit.io/develop/concepts/connections/secrets-management) y [Deploy your app on Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
