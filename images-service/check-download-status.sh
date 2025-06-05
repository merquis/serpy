#!/bin/bash

# Script para verificar el estado de descarga de imágenes

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# API Key (cambiar si es necesario)
API_KEY="serpy-demo-key-2025"
# Usar dominio público o localhost según prefieras
API_URL="https://images.videocursosweb.com"
# API_URL="http://localhost:8001"  # Alternativa local

echo -e "${GREEN}🔍 Verificador de Estado de Descarga de Imágenes${NC}\n"

# Si se proporciona un job_id como argumento, usarlo
if [ ! -z "$1" ]; then
    JOB_ID=$1
else
    # Listar jobs recientes
    echo -e "${YELLOW}📋 Jobs recientes:${NC}"
    curl -s "$API_URL/api/v1/jobs?limit=5" \
        -H "X-API-Key: $API_KEY" | jq -r '.[] | "\(.id) - \(.status) - \(.created_at)"' 2>/dev/null || \
        echo "No se pudieron listar los jobs. Verifica que el servicio esté funcionando."
    
    echo -e "\n${YELLOW}Ingresa el Job ID para verificar:${NC}"
    read JOB_ID
fi

if [ -z "$JOB_ID" ]; then
    echo -e "${RED}❌ No se proporcionó un Job ID${NC}"
    exit 1
fi

echo -e "\n${GREEN}📊 Estado del Job: $JOB_ID${NC}"

# Obtener estado del job
RESPONSE=$(curl -s "$API_URL/api/v1/jobs/$JOB_ID" -H "X-API-Key: $API_KEY")

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error al conectar con el servicio${NC}"
    exit 1
fi

# Parsear respuesta con jq si está disponible
if command -v jq &> /dev/null; then
    STATUS=$(echo "$RESPONSE" | jq -r '.status' 2>/dev/null)
    PROGRESS=$(echo "$RESPONSE" | jq -r '.progress' 2>/dev/null)
    TOTAL=$(echo "$RESPONSE" | jq -r '.metadata.total_documents' 2>/dev/null)
    DOWNLOADED=$(echo "$RESPONSE" | jq -r '.result.images_downloaded' 2>/dev/null)
    FAILED=$(echo "$RESPONSE" | jq -r '.result.failed_downloads' 2>/dev/null)
    
    echo -e "Estado: ${YELLOW}$STATUS${NC}"
    
    if [ "$STATUS" == "running" ]; then
        echo -e "Progreso: ${YELLOW}$PROGRESS${NC}"
    elif [ "$STATUS" == "completed" ]; then
        echo -e "${GREEN}✅ Descarga completada!${NC}"
        echo -e "Imágenes descargadas: ${GREEN}$DOWNLOADED${NC}"
        [ "$FAILED" != "null" ] && [ "$FAILED" -gt 0 ] && echo -e "Descargas fallidas: ${RED}$FAILED${NC}"
    elif [ "$STATUS" == "failed" ]; then
        echo -e "${RED}❌ La descarga falló${NC}"
        ERROR=$(echo "$RESPONSE" | jq -r '.error' 2>/dev/null)
        echo -e "Error: $ERROR"
    fi
    
    # Mostrar detalles adicionales
    echo -e "\n${YELLOW}📋 Detalles del Job:${NC}"
    echo "$RESPONSE" | jq '.' 2>/dev/null
else
    # Sin jq, mostrar respuesta raw
    echo "$RESPONSE"
fi

# Verificar imágenes descargadas
echo -e "\n${GREEN}📁 Verificando imágenes descargadas:${NC}"

IMAGES_DIR="/var/www/images"
if [ -d "$IMAGES_DIR" ]; then
    # Contar imágenes
    TOTAL_IMAGES=$(find "$IMAGES_DIR" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.webp" \) 2>/dev/null | wc -l)
    echo -e "Total de imágenes en el sistema: ${GREEN}$TOTAL_IMAGES${NC}"
    
    # Mostrar estructura de directorios recientes
    echo -e "\n${YELLOW}📂 Directorios recientes:${NC}"
    find "$IMAGES_DIR" -type d -mtime -1 -printf "%TY-%Tm-%Td %TH:%TM - %p\n" 2>/dev/null | sort -r | head -10
    
    # Espacio usado
    SPACE_USED=$(du -sh "$IMAGES_DIR" 2>/dev/null | cut -f1)
    echo -e "\n${YELLOW}💾 Espacio usado:${NC} $SPACE_USED"
else
    echo -e "${RED}❌ El directorio de imágenes no existe: $IMAGES_DIR${NC}"
fi

echo -e "\n${GREEN}✨ Verificación completada${NC}"
