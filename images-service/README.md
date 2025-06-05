# Microservicio de Gestión de Imágenes - SERPY

Microservicio escalable para la descarga y gestión de imágenes desde MongoDB, diseñado para integrarse en la arquitectura de microservicios de SERPY.

> **⚠️ IMPORTANTE**: Este servicio utiliza el puerto **8001** para evitar conflictos con el servicio API principal que usa el puerto 8000. Ver [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md) para más detalles.

```bash
curl https://images.serpsrewrite.com/api/v1/health
```
```bash
curl -X POST https://images.serpsrewrite.com/api/v1/download/collection/serpy_db/hotels \
  -H "X-API-Key: your-api-key"
```bash
curl -X POST https://images.serpsrewrite.com/api/v1/download/document/serpy_db/hotels/507f1f77bcf86cd799439011 \
  -H "X-API-Key: your-api-key"
```bash
curl -X POST https://images.serpsrewrite.com/api/v1/download/batch \
  -H "X-API-Key: your-api-key" \
```bash
curl https://images.serpsrewrite.com/api/v1/jobs?status=running \
  -H "X-API-Key: your-api-key"
```bash
curl https://images.serpsrewrite.com/api/v1/jobs/{job_id} \
  -H "X-API-Key: your-api-key"

- **API Docs**: https://images.serpsrewrite.com/docs (solo en desarrollo)
- **Flower** (Celery): http://localhost:5555

- **Métricas Prometheus**: https://images.serpsrewrite.com/api/v1/metrics

### Solución Implementada
- **Health Check**: https://images.serpsrewrite.com/api/v1/health

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

### 3. Crear la red Docker (si no existe)

```bash
docker network create serpy-network
```

### 4. Construir y ejecutar

```bash
docker-compose up -d
```

## 📖 Uso

### API Endpoints

#### Health Check
```bash
curl http://localhost:8001/api/v1/health
```

#### Descargar imágenes de una colección completa
```bash
curl -X POST http://localhost:8001/api/v1/download/collection/serpy_db/hotels \
  -H "X-API-Key: your-api-key"
```

#### Descargar imágenes de un documento específico
```bash
curl -X POST http://localhost:8001/api/v1/download/document/serpy_db/hotels/507f1f77bcf86cd799439011 \
  -H "X-API-Key: your-api-key"
```

#### Descarga batch con filtros
```bash
curl -X POST http://localhost:8001/api/v1/download/batch \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "database": "serpy_db",
    "collection": "hotels",
    "filter": {"city": "Madrid"},
    "limit": 50
  }'
```

#### Listar jobs
```bash
curl http://localhost:8001/api/v1/jobs?status=running \
  -H "X-API-Key: your-api-key"
```

#### Ver estado de un job
```bash
curl http://localhost:8001/api/v1/jobs/{job_id} \
  -H "X-API-Key: your-api-key"
```

### Estructura de almacenamiento

Las imágenes se almacenan en:
```
/images/
└── {database}/
    └── {collection}/
        └── {document_id}-{search_field}/
            ├── original/
            │   ├── img_001.jpg
            │   └── img_002.jpg
            ├── processed/         # Preparado para futuro
            └── metadata.json
```

## 🔧 Desarrollo

### Ejecutar en modo desarrollo

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar API
python -m uvicorn app.main:app --reload

# Ejecutar worker de Celery
celery -A app.workers.celery_app worker --loglevel=debug

# Ejecutar Flower (monitoreo)
celery -A app.workers.celery_app flower
```

### Tests

```bash
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html
```

## 📊 Monitoreo

- **API Docs**: http://localhost:8001/docs (solo en desarrollo)
- **Flower** (Celery): http://localhost:5555
- **Métricas Prometheus**: http://localhost:8001/api/v1/metrics
- **Health Check**: http://localhost:8001/api/v1/health

## 🏗️ Arquitectura

### Componentes

1. **API Service** (FastAPI)
   - Gestión de jobs
   - Endpoints REST
   - Autenticación por API Key

2. **Worker Service** (Celery)
   - Procesamiento asíncrono
   - Descarga de imágenes
   - Gestión de concurrencia

3. **Redis**
   - Cola de mensajes
   - Cache de resultados

4. **MongoDB**
   - Almacenamiento de jobs
   - Fuente de datos

### Patrones de diseño

- **Repository Pattern**: Acceso a datos
- **Strategy Pattern**: Procesamiento de imágenes
- **Factory Pattern**: Creación de procesadores
- **Dependency Injection**: Con FastAPI

## 🔒 Seguridad

- Autenticación por API Key
- CORS configurado
- Validación de inputs
- Sanitización de nombres de archivo
- Límites de rate

## 🚦 Estados de Jobs

- `pending`: En cola esperando procesamiento
- `running`: Procesándose actualmente
- `completed`: Completado exitosamente
- `failed`: Falló durante el procesamiento
- `cancelled`: Cancelado por el usuario

## 📝 Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `API_KEY` | Clave de API para autenticación | `secure-api-key-here` |
| `MONGODB_URI` | URI de conexión a MongoDB | `mongodb://mongo:27017` |
| `REDIS_URL` | URL de Redis | `redis://redis:6379/0` |
| `MAX_CONCURRENT_DOWNLOADS` | Descargas simultáneas máximas | `20` |
| `STORAGE_PATH` | Ruta de almacenamiento | `/images` |

Ver `.env.example` para la lista completa.

## 🐛 Troubleshooting

### El servicio no se conecta a MongoDB
- Verificar que MongoDB esté ejecutándose
- Comprobar que esté en la red `serpy-network`
- Revisar la URI de conexión en `.env`

### Las imágenes no se descargan
- Verificar logs: `docker logs images-worker`
- Comprobar que Redis esté funcionando
- Revisar permisos en `/var/www/images`

### Error de permisos al guardar imágenes
```bash
sudo chown -R $USER:$USER /var/www/images
# o
sudo chmod -R 755 /var/www/images
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crear una rama (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto es parte de SERPY y está bajo la misma licencia del proyecto principal.
