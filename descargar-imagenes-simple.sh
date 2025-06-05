#!/bin/bash

# Script para descargar imágenes usando el endpoint simple
# Las imágenes se guardarán en /root/images/

# Configuración
API_BASE="https://images.videocursosweb.com"
API_KEY="serpy-demo-key-2025"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Función para descargar imágenes
download_images_simple() {
    local api_url=$1
    local collection_name=$2
    
    echo -e "${BLUE}=== Descargando imágenes ===${NC}"
    echo -e "API URL: ${YELLOW}$api_url${NC}"
    echo -e "Collection: ${YELLOW}$collection_name${NC}"
    echo ""
    
    # Construir URL completa
    full_url="${API_BASE}/api/v1/download/from-api-url-simple?api_url=${api_url}&collection_name=${collection_name}"
    
    echo -e "${BLUE}Ejecutando petición...${NC}"
    
    # Hacer la petición y guardar respuesta
    response=$(curl -s -X POST "$full_url" \
        -H "X-API-Key: $API_KEY")
    
    # Mostrar respuesta formateada
    echo -e "${GREEN}Respuesta:${NC}"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    
    # Extraer información de la respuesta
    status=$(echo "$response" | jq -r '.status' 2>/dev/null)
    message=$(echo "$response" | jq -r '.message' 2>/dev/null)
    downloaded=$(echo "$response" | jq -r '.downloaded' 2>/dev/null)
    failed=$(echo "$response" | jq -r '.failed' 2>/dev/null)
    
    if [ "$status" = "success" ]; then
        echo ""
        echo -e "${GREEN}✓ Descarga completada${NC}"
        echo -e "Imágenes descargadas: ${GREEN}$downloaded${NC}"
        echo -e "Imágenes fallidas: ${YELLOW}$failed${NC}"
        
        # Verificar archivos en el VPS
        echo ""
        echo -e "${BLUE}Verificando archivos en /root/images:${NC}"
        
        # Buscar archivos recién creados (últimos 5 minutos)
        echo -e "${YELLOW}Archivos descargados recientemente:${NC}"
        find /root/images -type f -mmin -5 -ls | tail -20
        
        # Contar total de archivos
        total_files=$(find /root/images -type f | wc -l)
        echo ""
        echo -e "${GREEN}Total de archivos en /root/images: $total_files${NC}"
        
        # Mostrar tamaño total
        echo -e "${GREEN}Tamaño total:${NC}"
        du -sh /root/images/
    else
        echo ""
        echo -e "${RED}✗ Error en la descarga${NC}"
        echo -e "Mensaje: $message"
    fi
}

# Función para mostrar uso
show_usage() {
    echo "Uso: $0 <api_url> <collection_name>"
    echo ""
    echo "Ejemplo:"
    echo "  $0 \"https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b\" \"hotel-booking\""
    echo ""
    echo "O usa el comando curl directamente:"
    echo "  curl -X POST \"${API_BASE}/api/v1/download/from-api-url-simple?api_url=<API_URL>&collection_name=<COLLECTION>\" -H \"X-API-Key: $API_KEY\""
}

# Main
echo -e "${BLUE}=== Descarga de imágenes (Endpoint Simple) ===${NC}"
echo -e "${YELLOW}Las imágenes se guardarán en: /root/images/${NC}"
echo ""

# Verificar argumentos
if [ $# -lt 2 ]; then
    # Si no hay argumentos, mostrar ejemplos
    echo -e "${YELLOW}Ejemplos de uso:${NC}"
    echo ""
    
    # Ejemplo 1
    echo -e "${GREEN}1. Descargar imágenes de un hotel específico:${NC}"
    echo "curl -X POST \"${API_BASE}/api/v1/download/from-api-url-simple?api_url=https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking\" -H \"X-API-Key: $API_KEY\""
    echo ""
    
    # Ejemplo 2 - con este script
    echo -e "${GREEN}2. Usando este script:${NC}"
    echo "./descargar-imagenes-simple.sh \"https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b\" \"hotel-booking\""
    echo ""
    
    # Ejemplo 3 - múltiples hoteles
    echo -e "${GREEN}3. Script para descargar múltiples hoteles:${NC}"
    echo "# Crear un archivo con IDs de hoteles y ejecutar en bucle"
    echo "for hotel_id in 6840bc4e949575a0325d921b 6840bc4e949575a0325d921c 6840bc4e949575a0325d921d; do"
    echo "    ./descargar-imagenes-simple.sh \"https://api.videocursosweb.com/hotel-booking/\$hotel_id\" \"hotel-booking\""
    echo "    sleep 2"
    echo "done"
    echo ""
    
    show_usage
else
    # Ejecutar descarga con los argumentos proporcionados
    download_images_simple "$1" "$2"
fi

echo ""
echo -e "${BLUE}=== Comandos útiles ===${NC}"
echo "• Ver imágenes descargadas: find /root/images -type f -name '*.jpg' -o -name '*.png' | wc -l"
echo "• Ver estructura: tree -L 3 /root/images/"
echo "• Ver últimas descargas: find /root/images -type f -mmin -10 -ls"
echo "• Espacio usado: du -sh /root/images/"
