#!/bin/bash
set -e

echo "🚀 Iniciando servicio de imágenes..."

# Configurar variables de entorno por defecto si no están definidas
export API_PORT=${API_PORT:-8001}
export API_KEY=${API_KEY:-serpy-demo-key-2025}
export MONGODB_URI=${MONGODB_URI:-mongodb://host.docker.internal:27017}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
export CELERY_BROKER_URL=${CELERY_BROKER_URL:-redis://localhost:6379/0}
export CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}

echo "📋 Configuración:"
echo "   API_PORT: $API_PORT"
echo "   API_KEY: $API_KEY"
echo "   MONGODB_URI: $MONGODB_URI"
echo "   REDIS_URL: $REDIS_URL"

# Esperar a que Redis esté listo
echo "⏳ Esperando a Redis..."
sleep 2

# Generar supervisord.conf desde el template
echo "🔧 Generando configuración de supervisor..."
envsubst < /etc/supervisor/conf.d/supervisord.conf.template > /etc/supervisor/conf.d/supervisord.conf

# Iniciar supervisor
echo "✅ Iniciando supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
