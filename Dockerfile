# Servicio de productos (Flask + gunicorn)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=production

WORKDIR /app

# Dependencias primero (aprovecha la caché de capas)
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app.py wsgi.py ./

# El proceso no corre como root
RUN useradd --no-create-home --uid 1000 app
USER app

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT', '8082'), timeout=4)" || exit 1

# Servidor WSGI de producción (el servidor de desarrollo de Flask no se usa en el contenedor).
# --preload crea la tabla y los datos iniciales una sola vez, antes de lanzar los workers.
CMD ["sh", "-c", "exec gunicorn --preload --bind 0.0.0.0:${PORT:-8082} --workers ${WEB_CONCURRENCY:-2} --access-logfile - wsgi:app"]
