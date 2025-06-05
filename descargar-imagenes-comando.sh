#!/bin/bash

echo "🚀 Descargando imágenes desde el servicio Docker"
echo "=============================================="
echo ""

# El contenedor está escuchando en el puerto 8001
# Puedes usar localhost o la IP del contenedor

echo "📡 Ejecutando comando de descarga..."
echo ""

# Opción 1: Usando el endpoint original (requiere MongoDB)
echo "Probando endpoint original..."
curl -X POST "http://localhost:8001/api/v1/download/from-api-url" \
  -H "X-API-Key: serpy-demo-key-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "api_url": "https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b",
    "collection_name": "hotel-booking"
  }'

echo ""
echo ""

# Si el anterior falla, probar el endpoint simplificado
echo "Si el anterior falló, probando endpoint simplificado..."
curl -X POST "http://localhost:8001/api/v1/download/from-api-url-simple?api_url=https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking" \
  -H "X-API-Key: serpy-demo-key-2025"

echo ""
echo ""
echo "✅ Las imágenes se guardarán en: /var/www/images/serpy_db/hotel-booking/"
echo ""
echo "Para verificar:"
echo "  ls -la /var/www/images/serpy_db/hotel-booking/"
