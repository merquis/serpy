#!/bin/bash

echo "🔍 Verificación del Servicio de Imágenes"
echo "========================================"
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# URL base (cambiar según necesites)
if [ "$1" == "local" ]; then
    BASE_URL="http://localhost:8001"
    echo "Usando URL local: $BASE_URL"
else
    BASE_URL="https://images.serpsrewrite.com"
    echo "Usando URL pública: $BASE_URL"
fi

echo ""

# 1. Verificar salud del servicio
echo "1️⃣ Verificando salud del servicio..."
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/api/v1/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✅ Servicio saludable${NC}"
    echo "$HEALTH_RESPONSE" | grep -v "HTTP_CODE:" | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE" | grep -v "HTTP_CODE:"
else
    echo -e "${RED}❌ Error al conectar con el servicio (HTTP $HTTP_CODE)${NC}"
    exit 1
fi

echo ""

# 2. Probar diferentes API keys
echo "2️⃣ Probando API keys..."
API_KEYS=(
    "serpy-demo-key-2025"
    "secure-api-key-here"
    "tu-api-key-segura-aqui"
)

VALID_KEY=""
for key in "${API_KEYS[@]}"; do
    echo -n "   Probando: $key ... "
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/api/v1/jobs?limit=1" -H "X-API-Key: $key")
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
    
    if [ "$HTTP_CODE" == "200" ]; then
        echo -e "${GREEN}✅ Válida${NC}"
        VALID_KEY=$key
        break
    else
        echo -e "${RED}❌ Inválida (HTTP $HTTP_CODE)${NC}"
    fi
done

if [ -z "$VALID_KEY" ]; then
    echo ""
    echo -e "${RED}❌ No se encontró una API key válida${NC}"
    echo ""
    echo "Posibles soluciones:"
    echo "1. Verificar la API key en el servidor"
    echo "2. Actualizar el archivo .env"
    echo "3. Reiniciar el servicio con docker-compose restart"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ API Key válida encontrada: $VALID_KEY${NC}"
echo ""

# 3. Mostrar comando para descargar
echo "3️⃣ Comando para descargar imágenes:"
echo ""
echo "curl -X POST \"$BASE_URL/api/v1/download/from-api-url\" \\"
echo "  -H \"X-API-Key: $VALID_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{"
echo "    \"api_url\": \"https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b\","
echo "    \"collection_name\": \"hotel-booking\""
echo "  }'"
echo ""

# 4. Comando en una línea
echo "4️⃣ Comando en una línea:"
echo ""
echo -e "${YELLOW}curl -X POST \"$BASE_URL/api/v1/download/from-api-url?api_url=https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking\" -H \"X-API-Key: $VALID_KEY\"${NC}"
echo ""

# 5. Información adicional
echo "5️⃣ Información adicional:"
echo "   - Puerto del servicio: 8001"
echo "   - Las imágenes se guardan en: /var/www/images/"
echo "   - Para ver logs: docker-compose logs -f"
echo ""

echo -e "${GREEN}✅ Verificación completada${NC}"
