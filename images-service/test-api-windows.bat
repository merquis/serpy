@echo off
echo ========================================
echo  Probando conexion al servicio de imagenes
echo ========================================
echo.

echo 1. Probando endpoint de salud (sin API key):
curl -s https://images.videocursosweb.com/api/v1/health
echo.
echo.

echo 2. Probando con API key: serpy-demo-key-2025
curl -s -I https://images.videocursosweb.com/api/v1/jobs?limit=1 -H "X-API-Key: serpy-demo-key-2025"
echo.

echo 3. Comando para descargar imagenes:
echo.
echo curl -X POST "https://images.videocursosweb.com/api/v1/download/from-api-url?api_url=https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking" -H "X-API-Key: serpy-demo-key-2025"
echo.

pause
