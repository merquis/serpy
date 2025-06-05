#!/bin/bash

echo "🚀 Probando endpoint simplificado (sin MongoDB)"
echo "=============================================="
echo ""

# Configuración
BASE_URL="https://images.videocursosweb.com"
API_KEY="serpy-demo-key-2025"
API_URL="https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b"

echo "📡 Comando para descargar imágenes (endpoint simplificado):"
echo ""
echo "curl -X POST \"$BASE_URL/api/v1/download/from-api-url-simple?api_url=$API_URL&collection_name=hotel-booking\" \\"
echo "  -H \"X-API-Key: $API_KEY\""
echo ""
echo "Ejecutando..."
echo ""

# Ejecutar comando
curl -X POST "$BASE_URL/api/v1/download/from-api-url-simple?api_url=$API_URL&collection_name=hotel-booking" \
  -H "X-API-Key: $API_KEY" \
  -H "Accept: application/json"

echo ""
echo ""
echo "✅ Si el comando funcionó, las imágenes se guardarán en:"
echo "   /var/www/images/serpy_db/hotel-booking/"
echo ""
echo "❌ Si falló con 'API key inválida', necesitas:"
echo "   1. Actualizar el código en el servidor"
echo "   2. Reiniciar el servicio"
echo ""
echo "💡 Alternativa: Usa el script Python directamente:"
echo "   python3 download-direct.py"
