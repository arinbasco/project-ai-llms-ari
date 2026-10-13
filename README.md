# La Redacción

Herramienta interna de Digital Content para redactar textos de clientes. A partir de un pedido (cliente, plataforma, audiencia, objetivo y tema), el sistema:

1. **Redacta** el texto con un modelo de Groq, siguiendo la ficha del cliente.
2. **Revisa** el texto en dos capas: reglas comprobadas con código (expresiones vetadas, hashtags, trato, emojis...) y un segundo modelo que señala lo que el texto dice más allá del pedido.
3. **Corrige**: si encuentra problemas corregibles, pide una reescritura y la vuelve a revisar.

La interfaz web (Streamlit) muestra la versión original con las frases señaladas resaltadas, la versión corregida al lado, las notas del redactor y la lista de lo que encontró la revisión.

## Estructura

```
app.py                      Interfaz web (punto de entrada)
src/redaccion/
  redactor.py               Redacción y reescritura
  verificador.py            Revisión en dos capas
  prompts.py                Prompts y valores válidos de plataforma, audiencia y objetivo
  clientes.py               Carga de fichas de cliente
  presentacion.py           Notas, orden de problemas y resaltado para la interfaz
  limite.py                 Contador de pedidos diarios
  llm.py                    Conexión con Groq
data/clientes/              Una ficha JSON por cliente
assets/                     Logo y estilos
.streamlit/config.toml      Tema de la interfaz
.streamlit/secrets.example.toml   Plantilla de los secretos
scripts/cifrar_contrasena.py      Cifra contraseñas para los usuarios
tests/                      Pruebas (pytest)
```

## Puesta en marcha en local

Requiere Python 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; en macOS o Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### Secretos

Todo lo privado va en `.streamlit/secrets.toml`, el mismo archivo en local, en Docker y en la nube. Está en `.gitignore` y no se sube nunca.

1. Copia la plantilla: `.streamlit/secrets.example.toml` → `.streamlit/secrets.toml`.
2. Pon tu clave de Groq y los modelos.
3. Cambia `cookie.key` por una cadena larga y aleatoria. Por ejemplo, la salida de:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
4. Crea los usuarios (ver abajo).

`app.py` copia `GROQ_API_KEY`, `GROQ_MODEL` y `GROQ_MODEL_REVISOR` de los secretos a variables de entorno al arrancar, así que `llm.py` funciona igual en todas partes. Los scripts de `scripts/` siguen leyendo el `.env`, como antes.

### Usuarios

Cada usuario es un bloque en `secrets.toml`:

```toml
[credentials.usernames.lucia]       # "lucia" es el usuario con el que se entra, en minúsculas
name = "Lucía Pérez"                # nombre que se ve en la barra lateral
email = "lucia@digitalcontent.es"
password = "$2b$12$..."             # contraseña cifrada, nunca en claro
```

Para obtener la contraseña cifrada:

```bash
python scripts/cifrar_contrasena.py
```

Pide la contraseña dos veces sin mostrarla y escribe la línea `password = "..."` para pegarla en el bloque. Los usuarios no se pueden registrar desde la interfaz: para añadir o quitar uno, se edita `secrets.toml` (o el campo Secrets en la nube).

### Arrancar

```bash
streamlit run app.py
```

Se abre en http://localhost:8501.

### Pruebas

```bash
pytest
```

No llaman a Groq: usan modelos falsos.

## Límite de pedidos

Cada usuario puede hacer **10 pedidos al día** (constante `PEDIDOS_POR_DIA` en `app.py`). Un pedido solo cuenta si el redactor responde: si falla la conexión o se agota la cuota de Groq, no se descuenta.

El contador vive en la memoria de la app, compartido por todas las sesiones. Sobrevive a las recargas de la página, pero **se pone a cero si la app se reinicia**. El día es el del servidor: en Community Cloud, la hora UTC.

## Docker

La imagen lleva el código, las fichas de cliente y los recursos, pero **no los secretos**: se montan al arrancar el contenedor.

### Construir la imagen

```bash
docker build -t la-redaccion .
```

- `docker build` construye una imagen a partir del `Dockerfile` de la carpeta.
- `-t la-redaccion` le pone el nombre `la-redaccion`.
- `.` es la carpeta que se envía a Docker. Lo que aparece en `.dockerignore` (entorno virtual, `.env`, `secrets.toml`, `.git`, `docs/`, pruebas, cachés) se queda fuera.

### Ejecutar el contenedor

Windows (PowerShell):

```powershell
docker run --rm -p 8501:8501 -v "${PWD}\.streamlit\secrets.toml:/app/.streamlit/secrets.toml:ro" la-redaccion
```

macOS o Linux:

```bash
docker run --rm -p 8501:8501 -v "$(pwd)/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro" la-redaccion
```

- `--rm` borra el contenedor al pararlo. La imagen se queda.
- `-p 8501:8501` conecta el puerto 8501 de tu ordenador con el 8501 del contenedor, donde escucha Streamlit.
- `-v origen:destino:ro` monta tu `secrets.toml` dentro del contenedor, en la ruta donde lo busca Streamlit. `ro` lo monta en solo lectura.
- `la-redaccion` es la imagen que se ejecuta.

Después, abre http://localhost:8501. Para pararlo, Ctrl+C.

El contenedor usa Python 3.13, se ejecuta con un usuario sin permisos de administrador y tiene una comprobación de salud en `/_stcore/health`.

## Despliegue en Streamlit Community Cloud

El repositorio ya está preparado: `app.py` y `requirements.txt` están en la raíz y las versiones están fijadas.

1. Sube los cambios a `main` en GitHub. Comprueba que `.streamlit/secrets.toml` **no** está en el repositorio.
2. Entra en https://share.streamlit.io con la cuenta de GitHub que tiene acceso al repositorio.
3. Pulsa **Create app** y elige desplegar desde un repositorio de GitHub.
4. Rellena:
   - **Repository**: este repositorio.
   - **Branch**: `main`.
   - **Main file path**: `app.py`.
   - **App URL**: el subdominio que quieras.
5. Abre **Advanced settings**:
   - **Python version**: `3.13`. Por defecto Community Cloud usa la 3.12, así que hay que cambiarla.
   - **Secrets**: pega el contenido de tu `secrets.toml` con los valores de producción: clave de Groq, una `cookie.key` distinta de la de local y los usuarios con contraseñas cifradas.
6. Pulsa **Deploy**. La primera instalación tarda unos minutos.

Para cambiar los secretos más tarde (por ejemplo, para añadir un usuario): en el panel de la app, **Settings → Secrets**. La app se reinicia al guardar, y con ello el contador de pedidos vuelve a cero.

Cada `push` a `main` actualiza la app automáticamente.

## Persistencia

No hay base de datos. Eso implica que:

- **No se guarda historial** de pedidos. Si se quiere conservar un texto, hay que descargarlo o copiarlo.
- **Los clientes solo se crean añadiendo un JSON** a `data/clientes/` en el repositorio (con el formato de las fichas existentes) y subiéndolo.
- **El contador diario se pone a cero si la app se reinicia.** En Community Cloud la app se reinicia al desplegar cambios, al editar los secretos y cuando la plataforma lo necesita. Además, se duerme tras un tiempo sin visitas.

Community Cloud no conserva los archivos que escribe la app: cada reinicio empieza desde una copia limpia del repositorio. Por eso el contador no se guarda en un archivo.

## Trabajo futuro

- Base de datos externa para el historial de pedidos, las fichas de cliente y el contador.
- LangSmith para la trazabilidad de las llamadas al modelo.
