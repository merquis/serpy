# 🔧 Solución de Problemas - Servicio de Imágenes

## Problemas Identificados

1. **Puerto incorrecto**: El servicio está usando puerto 8000 en lugar de 8001
2. **MongoDB no conecta**: Intenta conectar a `mongo:27017` (hostname incorrecto)
3. **API Key inválida**: La configuración no se está aplicando correctamente

## Solución Paso a Paso

### 1. Detener el servicio actual
```bash
docker-compose down
docker stop serpy-images-service
docker rm serpy-images-service
```

### 2. Verificar la configuración
```bash
# Verificar que el .env tiene los valores correctos
cat .env | grep -E "API_PORT|API_KEY|MONGODB_URI"
```

Debe mostrar:
```
API_PORT=8001
API_KEY=serpy-demo-key-2025
MONGODB_URI=mongodb://host.docker.internal:27017
```

### 3. Limpiar y reconstruir
```bash
# Limpiar imágenes antiguas
docker rmi serpy-images-service

# Reconstruir con la configuración correcta
docker-compose build --no-cache

# Iniciar el servicio
docker-compose up -d
```

### 4. Verificar logs
```bash
# Ver logs en tiempo real
docker-compose logs -f

# Verificar que use puerto 8001
docker-compose logs | grep "8001"
```

### 5. Si usas EasyPanel

En EasyPanel, verifica estas variables de entorno:

```env
API_PORT=8001
API_KEY=serpy-demo-key-2025
MONGODB_URI=mongodb://[IP_DEL_HOST]:27017
```

Donde `[IP_DEL_HOST]` puede ser:
- La IP del servidor donde está MongoDB
- `host.docker.internal` (en algunos casos)
- El nombre del contenedor MongoDB si está en la misma red

### 6. Configuración alternativa para MongoDB

Si MongoDB está en el mismo servidor pero fuera de Docker:

```bash
# Obtener la IP del host Docker
ip addr show docker0 | grep inet

# Actualizar .env con esa IP (ejemplo: 172.17.0.1)
MONGODB_URI=mongodb://172.17.0.1:27017
```

### 7. Comando de prueba final

Una vez solucionado:

```bash
# Verificar salud
curl https://images.serpsrewrite.com/api/v1/health

# Descargar imágenes
curl -X POST "https://images.serpsrewrite.com/api/v1/download/from-api-url?api_url=https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking" -H "X-API-Key: serpy-demo-key-2025"
```

## Script de Diagnóstico Rápido

```bash
#!/bin/bash
echo "🔍 Diagnóstico del servicio"
echo ""
echo "1. Puerto configurado:"
docker exec serpy-images-service printenv API_PORT || echo "No se puede leer"
echo ""
echo "2. API Key configurada:"
docker exec serpy-images-service printenv API_KEY || echo "No se puede leer"
echo ""
echo "3. MongoDB URI:"
docker exec serpy-images-service printenv MONGODB_URI || echo "No se puede leer"
echo ""
echo "4. Procesos activos:"
docker exec serpy-images-service supervisorctl status
```

## Resumen

El problema principal es que el contenedor no está usando la configuración actualizada. Necesitas:

1. **Detener completamente** el servicio actual
2. **Reconstruir** la imagen con `docker-compose build --no-cache`
3. **Verificar** que MongoDB sea accesible desde el contenedor
4. **Reiniciar** con la configuración correcta

Si el problema persiste, es probable que necesites actualizar la configuración directamente en el servidor donde está desplegado el servicio.
