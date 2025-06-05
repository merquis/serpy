# Configuración del Microservicio de Imágenes en EasyPanel

## 🚀 Despliegue en EasyPanel

### 1. Preparar el código

```bash
# En tu repositorio local
cd images-service
git add .
git commit -m "Microservicio de imágenes listo para EasyPanel"
git push origin main
```

### 2. Crear la aplicación en EasyPanel

1. En EasyPanel, crear una nueva aplicación
2. Seleccionar "Docker" como tipo
3. Configurar el repositorio Git

### 3. Configuración del Build

En la configuración de Build de EasyPanel:

- **Dockerfile Path**: `images-service/Dockerfile.easypanel`
- **Build Context**: `images-service`

### 4. Variables de entorno

Configurar las siguientes variables en EasyPanel:

```env
# MongoDB (usar la misma conexión que los otros servicios)
MONGODB_URI=mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin
MONGODB_DATABASE=serpy_db

# API Key (generar una segura)
API_KEY=tu-api-key-segura-aqui

# Opcional: Webhook para notificaciones
WEBHOOK_URL=https://tu-n8n-instance.com/webhook/images-completed

# Configuración de descarga
MAX_CONCURRENT_DOWNLOADS=20
DOWNLOAD_TIMEOUT=30
```

### 5. Volúmenes

Crear un volumen persistente para las imágenes:

- **Mount Path**: `/images`
- **Size**: Según tus necesidades (ej: 50GB)

### 6. Red

Asegurarse de que esté en la misma red que MongoDB:
- Network: `serpy-network` o la red donde esté MongoDB

### 7. Puerto

- **Container Port**: 8001
- **Published Port**: El que prefieras (ej: 8003)

## 📋 Verificación post-despliegue

### Health Check
```bash
curl https://images.tudominio.com/api/v1/health
```

### Test de descarga
```bash
# Descargar imágenes de un documento específico
curl -X POST https://images.tudominio.com/api/v1/download/document/serpy_db/hotels/[DOCUMENT_ID] \
  -H "X-API-Key: tu-api-key-segura-aqui"
```

## 🔍 Monitoreo

### Ver logs en EasyPanel
Los logs de todos los procesos (API, Redis, Celery) están disponibles en la consola de EasyPanel.

### Verificar procesos internos
```bash
# Conectar al contenedor desde EasyPanel
docker exec -it [container-id] bash

# Ver estado de supervisor
supervisorctl status

# Ver logs específicos
tail -f /var/log/supervisor/api.log
tail -f /var/log/supervisor/celery.log
```

## 🎯 Uso del servicio

### Estructura de datos esperada

El servicio busca imágenes en documentos MongoDB con esta estructura:
```json
{
  "_id": "...",
  "nombre_alojamiento": "Hotel Example",
  "imagenes": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg",
    "https://example.com/image3.jpg"
  ]
}
```

### Almacenamiento de imágenes

Las imágenes se guardan en:
```
/images/
└── serpy_db/
    └── hotels/
        └── [document_id]-[nombre_sanitizado]/
            ├── original/
            │   ├── img_001.jpg
            │   ├── img_002.jpg
            │   └── img_003.jpg
            └── metadata.json
```

## 🛠️ Troubleshooting

### El servicio no arranca
1. Verificar logs en EasyPanel
2. Comprobar que las variables de entorno estén configuradas
3. Verificar conexión a MongoDB

### No se descargan imágenes
1. Verificar que el documento tenga el campo "imagenes"
2. Comprobar que las URLs sean accesibles
3. Revisar logs del worker: `tail -f /var/log/supervisor/celery.log`

### Error de permisos en volumen
En EasyPanel, verificar que el volumen tenga los permisos correctos o ejecutar:
```bash
docker exec -it [container-id] chown -R root:root /images
```

## 📊 Métricas y estadísticas

- **Jobs activos**: `GET /api/v1/jobs?status=running`
- **Métricas Prometheus**: `GET /api/v1/metrics`
- **Espacio usado**: Verificar en el volumen de EasyPanel

## 🔄 Actualización

Para actualizar el servicio:
1. Push cambios al repositorio
2. En EasyPanel, hacer click en "Redeploy"
3. El servicio se actualizará sin perder datos (volumen persistente)
