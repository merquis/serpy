#!/bin/bash

echo "==================================="
echo "Probando información de las APIs"
echo "==================================="
echo ""

echo "1. API Principal (api.serpsrewrite.com):"
echo "----------------------------------------"
curl -s https://api.serpsrewrite.com/ | python -m json.tool
echo ""
echo ""

echo "2. Servicio de Imágenes (images.serpsrewrite.com):"
echo "--------------------------------------------------"
curl -s https://images.serpsrewrite.com/ | python -m json.tool
echo ""
echo ""

echo "==================================="
echo "Prueba completada"
echo "==================================="
