#!/bin/bash

# Script rápido para descargar imágenes de un hotel específico

# Configuración
API_BASE="https://images.videocursosweb.com"
API_KEY="serpy-demo-key-2025"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Descarga de imágenes de hotel ===${NC}"
echo ""

# Hotel ID por defecto (puedes cambiarlo)
HOTEL_ID="${1:-6840bc4e949575a0325d921b}"
COLLECTION="hotel-booking"

echo -e "${YELLOW}Descargando imágenes del hotel: $HOTEL_ID${NC}"
echo -e "${YELLOW}Las imágenes se guardarán en: /root/images/${NC}"
echo ""

# Comando curl directo
echo -e "${BLUE}Ejecutando comando...${NC}"
curl -X POST "${API_BASE}/api/v1/download/from-api-url-simple?api_url=https://api.videocursosweb.com/hotel-booking/${HOTEL_ID}&collection_name=${COLLECTION}" \
    -H "X-API-Key: ${API_KEY}" \
    -H "Content-Type: application/json" | jq '.'

echo ""
echo -e "${GREEN}=== Verificando descarga ===${NC}"

# Esperar un momento para que se guarden los archivos
sleep 2

# Buscar archivos recién descargados
echo -e "${YELLOW}Archivos descargados (últimos 2 minutos):${NC}"
find /root/images -type f -mmin -2 -ls | tail -10

# Contar total
total=$(find /root/images -type f | wc -l)
echo ""
echo -e "${GREEN}Total de imágenes en /root/images: $total${NC}"

# Mostrar estructura específica del hotel
if [ -d "/root/images/serpy_db/hotel-booking" ]; then
    echo ""
    echo -e "${BLUE}Estructura de hotel-booking:${NC}"
    ls -la /root/images/serpy_db/hotel-booking/ | tail -10
fi

echo ""
echo -e "${BLUE}=== Otros comandos útiles ===${NC}"
echo "• Ver todas las imágenes: ls -la /root/images/serpy_db/hotel-booking/"
echo "• Contar imágenes JPG: find /root/images -name '*.jpg' | wc -l"
echo "• Ver tamaño total: du -sh /root/images/"
echo "• Descargar otro hotel: $0 <HOTEL_ID>"
