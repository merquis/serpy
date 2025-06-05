# 🔧 Solución Final - Servicio de Imágenes

## Estado Actual

El servicio de imágenes tiene los siguientes problemas que necesitan ser resueltos **en el servidor**:

### 1. **Problemas Identificados**
- ❌ El servicio usa puerto 8000 en lugar de 8001
- ❌ MongoDB intenta conectar a `mongo:27017` (hostname incorrecto)
- ❌ Las variables de entorno no se están aplicando correctamente
- ❌ La API key no coincide o no está configurada

### 2. **Cambios Realizados (en el repositorio)**

He actualizado los siguientes archivos para solucionar estos problemas:

1. **`supervisord.conf.template`** - Nuevo archivo que usa variables de entorno
2. **`entrypoint.sh`** - Actualizado para procesar variables correctamente
3. **`Dockerfile`** - Añadido `envsubst` para procesar templates
4. **`.env`** - Configurado con valores correctos

### 3. **Pasos para Aplicar en el Servidor**

**IMPORTANTE**: Estos cambios deben aplicarse en el servidor donde está desplegado el servicio.

#### Opción A: Si tienes acceso SSH al servidor

```bash
# 1. Conectar al servidor
ssh usuario@servidor

# 2. Ir al directorio del servicio
cd /path/to/images-service

# 3. Actualizar el código (pull desde git o copiar archivos)
git pull origin main

# 4. Detener el servicio actual
docker-compose down
docker stop serpy-images-service
docker rm serpy-images-service

# 5. Verificar/crear archivo .env con estos valores
cat > .env << EOF
API_PORT=8001
API_KEY=serpy-demo-key-2025
MONGODB_URI=mongodb://172.17.0.1:27017
MONGODB_DATABASE=serpy_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
STORAGE_PATH=/images
EOF

# 6. Reconstruir la imagen
docker-compose build --no-cache

# 7. Iniciar el servicio
docker-compose up -d

# 8. Verificar logs
docker-compose logs -f
```

#### Opción B: Si usas EasyPanel

1. Ve a la configuración de la aplicación en EasyPanel
2. Actualiza estas variables de entorno:
   ```
   API_PORT=8001
   API_KEY=serpy-demo-key-2025
   MONGODB_URI=mongodb://[IP-del-servidor-mongodb]:27017
   MONGODB_DATABASE=serpy_db
   ```
3. Actualiza el código (si es necesario)
4. Haz click en "Redeploy"

### 4. **Comando para Descargar Imágenes**

Una vez que el servicio esté funcionando correctamente:

```bash
# Comando en una línea
curl -X POST "https://images.videocursosweb.com/api/v1/download/from-api-url?api_url=https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking" -H "X-API-Key: serpy-demo-key-2025"

# O con JSON body
curl -X POST "https://images.videocursosweb.com/api/v1/download/from-api-url" \
  -H "X-API-Key: serpy-demo-key-2025" \
  -H "Content-Type: application/json" \
  -d '{"api_url":"https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b","collection_name":"hotel-booking"}'
```

### 5. **Verificación**

Para verificar que el servicio funciona:

```bash
# 1. Health check
curl https://images.videocursosweb.com/api/v1/health

# 2. Verificar con API key
curl https://images.videocursosweb.com/api/v1/jobs?limit=1 -H "X-API-Key: serpy-demo-key-2025"
```

### 6. **Scripts de Utilidad**

He creado varios scripts para ayudarte:

- `verify-service.sh` - Verifica el estado del servicio
- `test-api.py` - Prueba la API con Python
- `check-download-status.sh` - Verifica el estado de las descargas

### 7. **Resumen del Problema**

El problema principal es que **el servicio en el servidor no está usando la configuración actualizada**. Los cambios están en el repositorio pero necesitan ser aplicados en el servidor donde está ejecutándose el servicio.

## Próximos Pasos

1. **Aplicar los cambios en el servidor** (SSH o EasyPanel)
2. **Verificar que MongoDB sea accesible** desde el contenedor
3. **Reiniciar el servicio** con la configuración correcta
4. **Probar el comando de descarga**

Sin acceso al servidor para aplicar estos cambios, el servicio seguirá con los mismos problemas.
