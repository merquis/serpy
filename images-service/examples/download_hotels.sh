#!/bin/bash

# Configuración
API_URL="http://localhost:8003/api/v1"
API_KEY="tu-api-key-aqui"

echo "=== Descarga de imágenes de hoteles ==="

# 1. Verificar que el servicio está funcionando
echo "1. Verificando health del servicio..."
curl -s "$API_URL/health" | jq .

# 2. Descargar imágenes de un hotel específico (ejemplo)
echo -e "\n2. Descargando imágenes de un hotel específico..."
# Reemplaza DOCUMENT_ID con el ID real del documento
curl -X POST "$API_URL/download/document/serpy_db/hotel-booking/DOCUMENT_ID" \
  -H "X-API-Key: $API_KEY" | jq .

# 3. Ver el estado del job
echo -e "\n3. Verificando estado de jobs..."
curl -s "$API_URL/jobs" \
  -H "X-API-Key: $API_KEY" | jq .

# 4. Descargar toda la colección (¡cuidado, puede ser mucho!)
# echo -e "\n4. Descargando TODA la colección..."
# curl -X POST "$API_URL/download/collection/serpy_db/hotel-booking" \
#   -H "X-API-Key: $API_KEY" | jq .

# 5. Descargar con filtros
echo -e "\n5. Descargando hoteles con filtro..."
curl -X POST "$API_URL/download/batch" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "serpy_db",
    "collection": "hotel-booking",
    "filter": {"valoracion_global": {"$gte": 9}},
    "limit": 5
  }' | jq .
