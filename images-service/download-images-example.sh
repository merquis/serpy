#!/bin/bash

# Script de ejemplo para descargar imágenes desde una API externa

echo "🚀 Descargando imágenes desde API externa..."
echo ""

# URL de la API y configuración
API_URL="https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b"
SERVICE_URL="https://images.videocursosweb.com"  # Usando el dominio público
API_KEY="serpy-demo-key-2025"

echo "📡 Ejemplos de comandos de descarga:"
echo ""
echo "1️⃣ Comando en una línea con JSON:"
echo ""
echo "curl -X POST \"$SERVICE_URL/api/v1/download/from-api-url\" -H \"X-API-Key: $API_KEY\" -H \"Content-Type: application/json\" -d '{\"api_url\":\"$API_URL\",\"collection_name\":\"hotel-booking\"}'"
echo ""
echo "2️⃣ Comando en una línea con parámetros de query (más simple):"
echo ""
echo "curl -X POST \"$SERVICE_URL/api/v1/download/from-api-url?api_url=$API_URL&collection_name=hotel-booking\" -H \"X-API-Key: $API_KEY\""
echo ""
echo "---"
echo ""

# Ejecutar el comando (opción con parámetros de query)
echo "🚀 Ejecutando descarga..."
curl -X POST "$SERVICE_URL/api/v1/download/from-api-url?api_url=$API_URL&collection_name=hotel-booking" -H "X-API-Key: $API_KEY"

echo ""
echo ""
echo "✅ Comando ejecutado. El servicio devolverá un Job ID para seguimiento."
echo ""
echo "💡 Para verificar el estado, usa:"
echo "   ./check-download-status.sh [JOB_ID]"
echo ""
echo "📁 Las imágenes se guardarán en: /var/www/images/serpy_db/hotel-booking/"
