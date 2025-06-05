@echo off
echo ========================================
echo  Probando endpoint simplificado (sin MongoDB)
echo ========================================
echo.

REM Configuracion
set BASE_URL=https://images.serpsrewrite.com
set API_KEY=serpy-demo-key-2025
set API_URL=https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b

echo Comando para descargar imagenes (endpoint simplificado):
echo.
echo curl -X POST "%BASE_URL%/api/v1/download/from-api-url-simple?api_url=%API_URL%&collection_name=hotel-booking" -H "X-API-Key: %API_KEY%"
echo.
echo Ejecutando...
echo.

REM Ejecutar comando
curl -X POST "%BASE_URL%/api/v1/download/from-api-url-simple?api_url=%API_URL%&collection_name=hotel-booking" -H "X-API-Key: %API_KEY%" -H "Accept: application/json"

echo.
echo.
echo Si el comando funciono, las imagenes se guardaran en:
echo    /var/www/images/serpy_db/hotel-booking/
echo.
echo Si fallo con 'API key invalida', necesitas:
echo    1. Actualizar el codigo en el servidor
echo    2. Reiniciar el servicio
echo.
echo Alternativa: Usa el script Python directamente:
echo    python download-direct.py
echo.
pause
