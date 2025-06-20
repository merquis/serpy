FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema incluyendo Redis y curl
RUN apt-get update && apt-get install -y \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libwebp-dev \
    libheif-dev \
    libde265-dev \
    libffi-dev \
    redis-server \
    supervisor \
    curl \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app/ ./app/
COPY config/ ./config/
COPY download-direct.py /download-direct.py

# Crear directorios necesarios
RUN mkdir -p /images /var/log/supervisor /var/run/redis

# Copiar configuración de supervisor
COPY supervisord.conf.template /etc/supervisor/conf.d/supervisord.conf.template

# Script de inicio
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV REDIS_URL=redis://localhost:6379/0
ENV CELERY_BROKER_URL=redis://localhost:6379/0
ENV CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Exponer puerto
EXPOSE 8001

# Usar supervisor para ejecutar múltiples procesos
CMD ["/entrypoint.sh"]
