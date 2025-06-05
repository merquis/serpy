#!/bin/bash

echo "=== Configurando volumen de imágenes en EasyPanel ==="

# Crear directorio en el host si no existe
echo "1. Creando directorio /root/images en el host..."
mkdir -p /root/images
chmod -R 755 /root/images

echo ""
echo "2. Para aplicar el volumen en EasyPanel:"
echo ""
echo "   a) Ve a la configuración de tu servicio 'down-images' en EasyPanel"
echo "   b) En la sección 'Volumes', añade:"
echo "      - Host Path: /root/images"
echo "      - Container Path: /images"
echo "   c) Guarda y redespliega el servicio"
echo ""
echo "3. Una vez redeployado, las imágenes se guardarán en:"
echo "   - En el VPS (host): /root/images/"
echo "   - Dentro del contenedor: /images/"
echo ""
echo "4. Para verificar que funciona, ejecuta dentro del contenedor:"
echo "   ls -la /images"
echo ""
echo "5. Para descargar imágenes, usa:"
echo '   curl -X POST "https://images.serpsrewrite.com/api/v1/download/from-api-url-simple?api_url=https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking" -H "X-API-Key: serpy-demo-key-2025"'
