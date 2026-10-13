# Imagen de La Redacción. Los secretos no van dentro: se montan al arrancar
# el contenedor (ver README).
FROM python:3.13-slim

# Sin archivos .pyc, salida de Python sin búfer y sin caché de pip en la imagen.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Primero las dependencias, para que Docker las reutilice si solo cambia el código.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .
COPY src/ src/
COPY data/ data/
COPY assets/ assets/
COPY .streamlit/config.toml .streamlit/config.toml

# La app no necesita permisos de administrador.
RUN useradd --create-home redaccion
USER redaccion

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
