#!/bin/bash

# Script de configuración para VPS
# Este script configura el servicio de imágenes para ejecutarse en un VPS

echo "🚀 Configurando servicio de imágenes en VPS..."

# 1. Crear directorio para imágenes en el host
echo "📁 Creando directorio para imágenes..."
sudo mkdir -p /var/www/images
sudo chown -R $USER:$USER /var/www/images
sudo chmod -R 755 /var/www/images

# 2. Verificar si MongoDB está instalado localmente
echo "🔍 Verificando MongoDB..."
if ! command -v mongod &> /dev/null; then
    echo "⚠️  MongoDB no está instalado. Por favor, instálalo primero."
    echo "   Ubuntu/Debian: sudo apt-get install mongodb"
    echo "   O usa un servicio MongoDB remoto actualizando MONGODB_URI en .env"
fi

# 3. Crear archivo .env si no existe
if [ ! -f .env ]; then
    echo "📝 Creando archivo .env..."
    cp .env.example .env
    
    # Actualizar MongoDB URI para conexión local
    sed -i 's|MONGODB_URI=mongodb://mongo:27017|MONGODB_URI=mongodb://172.17.0.1:27017|g' .env
    
    echo "⚠️  Por favor, revisa y actualiza el archivo .env con tus valores"
fi

# 4. Crear red Docker si no existe
echo "🌐 Verificando red Docker..."
if ! docker network ls | grep -q serpy-network; then
    docker network create serpy-network
fi

# 5. Construir y ejecutar con docker-compose
echo "🏗️  Construyendo imagen Docker..."
docker-compose build

echo "🚀 Iniciando servicio..."
docker-compose up -d

# 6. Verificar que el servicio está funcionando
echo "⏳ Esperando a que el servicio inicie..."
sleep 10

echo "🔍 Verificando estado del servicio..."
if curl -s http://localhost:8001/api/v1/health > /dev/null; then
    echo "✅ Servicio iniciado correctamente!"
    echo ""
    echo "📋 Información del servicio:"
    echo "   - URL: http://localhost:8001"
    echo "   - Documentación API: http://localhost:8001/docs"
    echo "   - Directorio de imágenes: /var/www/images"
    echo ""
    echo "🔧 Comandos útiles:"
    echo "   - Ver logs: docker-compose logs -f"
    echo "   - Detener servicio: docker-compose down"
    echo "   - Reiniciar servicio: docker-compose restart"
    echo ""
    echo "📡 Ejemplo de uso desde el VPS:"
    echo "   curl -X POST http://localhost:8001/api/v1/download/from-api-url \\"
    echo "     -H \"X-API-Key: serpy-demo-key-2025\" \\"
    echo "     -H \"Content-Type: application/json\" \\"
    echo "     -d '{\"api_url\": \"https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b\"}'"
else
    echo "❌ Error: El servicio no responde. Revisa los logs con: docker-compose logs"
fi
