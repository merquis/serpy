#!/bin/bash

# Script para verificar el estado del volumen de imágenes

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== Verificación del volumen de imágenes ===${NC}"
echo ""

# 1. Verificar si el contenedor está corriendo
echo -e "${YELLOW}1. Estado del contenedor:${NC}"
if docker ps | grep -q serpy-images-service; then
    echo -e "${GREEN}✓ El contenedor está corriendo${NC}"
    docker ps | grep serpy-images-service
else
    echo -e "${RED}✗ El contenedor NO está corriendo${NC}"
    echo "Ejecuta: cd /root/serpy/images-service && docker-compose up -d"
    exit 1
fi

echo ""

# 2. Verificar el montaje del volumen
echo -e "${YELLOW}2. Verificando montaje del volumen:${NC}"
mount_info=$(docker inspect serpy-images-service | jq -r '.[0].Mounts[] | select(.Destination == "/images")')

if [ ! -z "$mount_info" ]; then
    echo -e "${GREEN}✓ Volumen montado correctamente${NC}"
    echo "Origen (VPS): $(echo $mount_info | jq -r '.Source')"
    echo "Destino (Container): $(echo $mount_info | jq -r '.Destination')"
else
    echo -e "${RED}✗ Volumen NO está montado${NC}"
fi

echo ""

# 3. Verificar directorio en el VPS
echo -e "${YELLOW}3. Directorio en el VPS (/root/images):${NC}"
if [ -d "/root/images" ]; then
    echo -e "${GREEN}✓ El directorio existe${NC}"
    echo "Permisos: $(ls -ld /root/images)"
    
    # Contar archivos
    total_files=$(find /root/images -type f 2>/dev/null | wc -l)
    total_dirs=$(find /root/images -type d 2>/dev/null | wc -l)
    
    echo "Total de directorios: $total_dirs"
    echo "Total de archivos: $total_files"
    
    if [ $total_files -gt 0 ]; then
        echo ""
        echo "Tipos de archivos:"
        find /root/images -type f -exec file -b --mime-type {} \; | sort | uniq -c
        
        echo ""
        echo "Tamaño total:"
        du -sh /root/images
    fi
else
    echo -e "${RED}✗ El directorio NO existe${NC}"
    echo "Creándolo..."
    mkdir -p /root/images
    chmod 755 /root/images
fi

echo ""

# 4. Verificar acceso desde el contenedor
echo -e "${YELLOW}4. Verificando acceso desde el contenedor:${NC}"
docker exec serpy-images-service ls -la /images > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ El contenedor puede acceder a /images${NC}"
    docker exec serpy-images-service ls -la /images | head -5
else
    echo -e "${RED}✗ El contenedor NO puede acceder a /images${NC}"
fi

echo ""

# 5. Test de escritura
echo -e "${YELLOW}5. Test de escritura:${NC}"
test_file="/images/test-$(date +%s).txt"
docker exec serpy-images-service bash -c "echo 'Test de escritura' > $test_file" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ El contenedor puede escribir en el volumen${NC}"
    
    # Verificar que el archivo existe en el VPS
    vps_file="/root$test_file"
    if [ -f "$vps_file" ]; then
        echo -e "${GREEN}✓ El archivo se creó correctamente en el VPS${NC}"
        echo "Archivo: $vps_file"
        
        # Limpiar archivo de test
        rm -f "$vps_file"
    else
        echo -e "${RED}✗ El archivo NO se creó en el VPS${NC}"
    fi
else
    echo -e "${RED}✗ El contenedor NO puede escribir en el volumen${NC}"
fi

echo ""

# 6. Mostrar estructura actual
if [ -d "/root/images" ] && [ $(find /root/images -type f 2>/dev/null | wc -l) -gt 0 ]; then
    echo -e "${YELLOW}6. Estructura actual de /root/images:${NC}"
    tree -L 3 /root/images 2>/dev/null || find /root/images -type d | sort | head -20
fi

echo ""
echo -e "${BLUE}=== Resumen ===${NC}"
echo "• Directorio de imágenes en VPS: /root/images"
echo "• Directorio de imágenes en contenedor: /images"
echo "• Para ver logs del servicio: docker logs serpy-images-service"
echo "• Para reiniciar con nueva config: cd /root/serpy/images-service && docker-compose down && docker-compose up -d"
