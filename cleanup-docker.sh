#!/bin/bash

echo "🧹 Limpieza de Docker - Eliminando contenedores y volúmenes no utilizados"
echo "========================================================================="
echo ""

# Mostrar estado actual
echo "📊 Estado actual:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
echo ""

# Preguntar confirmación
echo "⚠️  ADVERTENCIA: Esto eliminará:"
echo "   - Todos los contenedores detenidos"
echo "   - Todos los volúmenes no utilizados"
echo "   - Todas las imágenes no utilizadas"
echo "   - Todas las redes no utilizadas"
echo ""
read -p "¿Estás seguro? (s/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]
then
    echo ""
    echo "🗑️  Eliminando contenedores detenidos..."
    docker container prune -f
    
    echo ""
    echo "🗑️  Eliminando volúmenes no utilizados..."
    docker volume prune -f
    
    echo ""
    echo "🗑️  Eliminando imágenes no utilizadas..."
    docker image prune -a -f
    
    echo ""
    echo "🗑️  Eliminando redes no utilizadas..."
    docker network prune -f
    
    echo ""
    echo "✅ Limpieza completada!"
    echo ""
    echo "📊 Estado después de la limpieza:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
    echo ""
    echo "💾 Espacio liberado:"
    docker system df
else
    echo "❌ Limpieza cancelada"
fi
