#!/bin/bash

# Script para descargar imágenes desde el VPS con volumen montado

# Configuración
API_URL="http://localhost:8001/api/v1/download/from-api-url"
API_KEY="test-api-key-123"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Descarga de imágenes con volumen montado ===${NC}"
echo -e "${YELLOW}Las imágenes se guardarán en: /root/images/${NC}"
echo ""

# Verificar que el servicio está corriendo
if ! docker ps | grep -q serpy-images-service; then
    echo -e "${YELLOW}El servicio no está corriendo. Iniciándolo...${NC}"
    cd /root/serpy/images-service && docker-compose up -d
    sleep 5
fi

# Función para descargar imágenes
download_images() {
    local api_endpoint=$1
    local database=$2
    local collection=$3
    local search_field=$4
    local limit=${5:-10}
    
    echo -e "${BLUE}Descargando desde: $api_endpoint${NC}"
    echo "Database: $database, Collection: $collection, Field: $search_field, Limit: $limit"
    
    # Hacer la petición
    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "{
            \"api_url\": \"$api_endpoint\",
            \"database\": \"$database\",
            \"collection\": \"$collection\",
            \"search_field\": \"$search_field\",
            \"limit\": $limit
        }")
    
    # Mostrar respuesta
    echo -e "${GREEN}Respuesta:${NC}"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    
    # Extraer job_id si existe
    job_id=$(echo "$response" | jq -r '.job_id' 2>/dev/null)
    
    if [ ! -z "$job_id" ] && [ "$job_id" != "null" ]; then
        echo -e "${GREEN}Job ID: $job_id${NC}"
        echo ""
        
        # Esperar un momento para que se procesen algunas imágenes
        echo "Esperando 10 segundos para que se procesen algunas imágenes..."
        sleep 10
        
        # Verificar el estado del job
        echo -e "${BLUE}Verificando estado del job...${NC}"
        status_response=$(curl -s -X GET "http://localhost:8001/api/v1/jobs/$job_id/status" \
            -H "X-API-Key: $API_KEY")
        echo "$status_response" | jq '.' 2>/dev/null || echo "$status_response"
        
        # Verificar archivos descargados en el VPS
        echo ""
        echo -e "${BLUE}Verificando archivos descargados en /root/images:${NC}"
        
        # Buscar la carpeta específica
        folder_path="/root/images/$database/$collection"
        if [ -d "$folder_path" ]; then
            echo -e "${GREEN}Carpeta encontrada: $folder_path${NC}"
            echo "Contenido:"
            ls -la "$folder_path" | head -20
            
            # Contar archivos
            file_count=$(find "$folder_path" -type f | wc -l)
            echo ""
            echo -e "${GREEN}Total de archivos descargados: $file_count${NC}"
        else
            echo -e "${YELLOW}La carpeta $folder_path aún no existe${NC}"
        fi
    fi
    
    echo ""
    echo "----------------------------------------"
    echo ""
}

# Ejemplos de uso
echo -e "${BLUE}=== Ejemplos de descarga ===${NC}"
echo ""

# Ejemplo 1: Descargar hoteles de Mallorca
echo -e "${GREEN}1. Descargando hoteles de Mallorca (5 hoteles)...${NC}"
download_images \
    "http://api:8000/api/v1/hotels/booking/search?location=Mallorca,%20Espa%C3%B1a&page_size=5" \
    "serpy_db" \
    "hotels" \
    "mallorca" \
    5

# Esperar antes del siguiente ejemplo
sleep 5

# Ejemplo 2: Descargar hoteles de Barcelona
echo -e "${GREEN}2. Descargando hoteles de Barcelona (3 hoteles)...${NC}"
download_images \
    "http://api:8000/api/v1/hotels/booking/search?location=Barcelona,%20Espa%C3%B1a&page_size=3" \
    "serpy_db" \
    "hotels" \
    "barcelona" \
    3

# Resumen final
echo ""
echo -e "${BLUE}=== Resumen de descargas ===${NC}"
echo -e "${YELLOW}Directorio principal de imágenes: /root/images/${NC}"
echo ""
echo "Estructura de carpetas:"
tree -L 3 /root/images/ 2>/dev/null || find /root/images -type d | head -20

echo ""
echo -e "${GREEN}Para ver todas las imágenes descargadas:${NC}"
echo "  find /root/images -type f -name '*.jpg' -o -name '*.png' -o -name '*.webp' | wc -l"
echo ""
echo -e "${GREEN}Para ver el tamaño total:${NC}"
echo "  du -sh /root/images/"
