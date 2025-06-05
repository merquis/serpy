#!/bin/bash

echo "🔍 Verificando configuración del contenedor Docker"
echo "================================================"
echo ""

# Ver detalles del contenedor
echo "1. Información del contenedor:"
docker inspect down-images_down-images.1.msfmv2cjyank142xwnsa14w44 | grep -A 10 "PortBindings"

echo ""
echo "2. Puertos expuestos:"
docker port down-images_down-images.1.msfmv2cjyank142xwnsa14w44

echo ""
echo "3. Verificar si el servicio está escuchando dentro del contenedor:"
docker exec down-images_down-images.1.msfmv2cjyank142xwnsa14w44 netstat -tlnp | grep 8001 || echo "netstat no disponible"

echo ""
echo "4. Ver logs del contenedor:"
docker logs --tail 20 down-images_down-images.1.msfmv2cjyank142xwnsa14w44

echo ""
echo "5. Probar conexión directa al contenedor:"
# Obtener IP del contenedor
CONTAINER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' down-images_down-images.1.msfmv2cjyank142xwnsa14w44)
echo "IP del contenedor: $CONTAINER_IP"

if [ ! -z "$CONTAINER_IP" ]; then
    echo ""
    echo "6. Intentando curl directo a la IP del contenedor:"
    curl -X POST "http://$CONTAINER_IP:8001/api/v1/download/from-api-url?api_url=https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking" -H "X-API-Key: serpy-demo-key-2025"
fi

echo ""
echo "💡 Si el puerto no está mapeado, necesitas:"
echo "   - Reiniciar el contenedor con -p 8001:8001"
echo "   - O usar la IP interna del contenedor"
echo "   - O configurar EasyPanel para exponer el puerto"
