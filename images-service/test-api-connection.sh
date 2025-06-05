#!/bin/bash

echo "🔍 Probando conexión al servicio de imágenes"
echo ""

# Probar health check (no requiere API key)
echo "1️⃣ Probando endpoint de salud (sin API key):"
curl -s https://images.videocursosweb.com/api/v1/health | jq '.' 2>/dev/null || echo "Respuesta: $(curl -s https://images.videocursosweb.com/api/v1/health)"

echo ""
echo "2️⃣ Probando con diferentes API keys:"
echo ""

# Lista de posibles API keys para probar
API_KEYS=(
    "serpy-demo-key-2025"
    "secure-api-key-here"
    "tu-api-key-segura-aqui"
)

for key in "${API_KEYS[@]}"; do
    echo "Probando con API key: $key"
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" https://images.videocursosweb.com/api/v1/jobs?limit=1 -H "X-API-Key: $key")
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ API key válida: $key"
        echo ""
        echo "📡 Usa este comando para descargar:"
        echo "curl -X POST \"https://images.videocursosweb.com/api/v1/download/from-api-url?api_url=https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking\" -H \"X-API-Key: $key\""
        break
    else
        echo "❌ API key inválida (HTTP $HTTP_CODE)"
    fi
    echo ""
done

echo ""
echo "💡 Si ninguna API key funciona, necesitas:"
echo "1. Verificar la API key configurada en el servidor"
echo "2. Actualizar el archivo .env en el servidor"
echo "3. Reiniciar el servicio con: docker-compose restart"
