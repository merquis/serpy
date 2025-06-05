#!/bin/bash

echo "=== Verificando estructura de imágenes en /root/images ==="
echo ""

# Verificar si existe el directorio
if [ -d "/root/images" ]; then
    echo "Contenido de /root/images:"
    ls -la /root/images/
    echo ""
    
    # Mostrar estructura completa
    echo "Estructura completa (primeros 3 niveles):"
    find /root/images -type d -maxdepth 3 | sort
    echo ""
    
    # Contar archivos por directorio
    echo "Archivos por directorio:"
    for dir in $(find /root/images -type d -maxdepth 2); do
        count=$(find "$dir" -type f -name "*.jpg" -o -name "*.png" | wc -l)
        if [ $count -gt 0 ]; then
            echo "$dir: $count imágenes"
        fi
    done
else
    echo "El directorio /root/images no existe"
fi

echo ""
echo "=== Ejemplos de rutas completas de imágenes ==="
find /root/images -type f -name "*.jpg" | head -5
