#!/bin/bash
set -e

echo "🚀 Iniciando servicio de imágenes..."

# Esperar a que Redis esté listo
echo "⏳ Esperando a Redis..."
sleep 2

# Iniciar supervisor
echo "✅ Iniciando supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
