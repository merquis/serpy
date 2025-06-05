#!/bin/bash

echo "🔐 Verificación y Configuración de API Key"
echo ""

# Verificar la API key actual en el archivo .env
if [ -f ".env" ]; then
    echo "📋 API Key actual en .env:"
    grep "API_KEY=" .env
    echo ""
fi

# Si el servicio está ejecutándose con Docker, verificar la variable de entorno
if docker ps | grep -q serpy-images-service; then
    echo "🐳 API Key en el contenedor Docker:"
    docker exec serpy-images-service printenv API_KEY
    echo ""
fi

echo "❓ ¿Qué deseas hacer?"
echo "1) Usar la API key por defecto: serpy-demo-key-2025"
echo "2) Configurar una nueva API key"
echo "3) Ver la API key actual y salir"
echo ""
read -p "Selecciona una opción (1-3): " option

case $option in
    1)
        NEW_API_KEY="serpy-demo-key-2025"
        ;;
    2)
        read -p "Ingresa la nueva API key: " NEW_API_KEY
        ;;
    3)
        echo "✅ Verificación completada"
        exit 0
        ;;
    *)
        echo "❌ Opción inválida"
        exit 1
        ;;
esac

# Actualizar .env
if [ ! -z "$NEW_API_KEY" ]; then
    echo ""
    echo "📝 Actualizando .env con la nueva API key..."
    
    # Hacer backup del .env actual
    cp .env .env.backup
    
    # Actualizar API_KEY en .env
    sed -i "s/API_KEY=.*/API_KEY=$NEW_API_KEY/" .env
    
    echo "✅ .env actualizado"
    echo ""
    echo "🔄 Para aplicar los cambios, reinicia el servicio:"
    echo "   docker-compose down"
    echo "   docker-compose up -d"
    echo ""
    echo "📡 Luego puedes usar este comando para descargar:"
    echo ""
    echo "curl -X POST \"https://images.serpsrewrite.com/api/v1/download/from-api-url?api_url=https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking\" -H \"X-API-Key: $NEW_API_KEY\""
fi
