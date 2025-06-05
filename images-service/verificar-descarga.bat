@echo off
echo ========================================
echo  Verificador de Descarga de Imagenes
echo ========================================
echo.

echo 1. Verificando respuesta del comando...
echo.
echo Si ves un error 404: El nuevo endpoint NO esta disponible en el servidor
echo Si ves "API key invalida": El servicio esta activo pero la API key no coincide
echo Si ves un JSON con "status": "completed": La descarga fue exitosa!
echo.

echo 2. Para ver las imagenes descargadas en el servidor:
echo.
echo Conectate por SSH al servidor y ejecuta:
echo    ls -la /var/www/images/serpy_db/hotel-booking/
echo.
echo O si tienes acceso FTP/SFTP, navega a:
echo    /var/www/images/serpy_db/hotel-booking/
echo.

echo 3. Estructura esperada de archivos:
echo.
echo /var/www/images/
echo └── serpy_db/
echo     └── hotel-booking/
echo         └── [ID-del-hotel]-[nombre-hotel]/
echo             ├── original/
echo             │   ├── img_001.jpg
echo             │   ├── img_002.jpg
echo             │   └── ...
echo             └── metadata.json
echo.

echo 4. SOLUCION INMEDIATA (sin actualizar servidor):
echo.
echo Conectate al servidor por SSH y ejecuta:
echo    cd /path/to/images-service
echo    python3 download-direct.py
echo.
echo Esto descargara las imagenes directamente sin usar el servicio web.
echo.

echo 5. Para que funcione el comando curl:
echo.
echo El servidor necesita ser actualizado con:
echo    git pull
echo    docker-compose build --no-cache
echo    docker-compose restart
echo.

pause
