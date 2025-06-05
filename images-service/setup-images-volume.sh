#!/bin/bash

echo "=== Configurando volumen de imágenes en el VPS ==="

# Crear directorio en el VPS si no existe
echo "1. Creando directorio /root/images..."
mkdir -p /root/images

# Establecer permisos adecuados
echo "2. Estableciendo permisos..."
chmod -R 755 /root/images

# Detener el servicio actual
echo "3. Deteniendo el servicio actual..."
# Detectar la ruta actual del proyecto
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
docker-compose down

# Reconstruir y reiniciar con la nueva configuración
echo "4. Reconstruyendo y reiniciando el servicio..."
docker-compose up -d --build

# Verificar que el servicio está corriendo
echo "5. Verificando el servicio..."
sleep 5
docker-compose ps

# Verificar que el volumen está montado correctamente
echo "6. Verificando montaje del volumen..."
docker exec serpy-images-service ls -la /images

echo ""
echo "=== Configuración completada ==="
echo "Las imágenes ahora se guardarán en: /root/images"
echo ""
echo "Para verificar las descargas:"
echo "  - En el VPS: ls -la /root/images/"
echo "  - Dentro del contenedor: docker exec serpy-images-service ls -la /images"
