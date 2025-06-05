# Configuración de Puertos - Servicio de Imágenes

## ⚠️ IMPORTANTE: Conflicto de Puertos Resuelto

### Problema Original
- El servicio API principal usa el puerto **8000**
- El servicio de imágenes estaba configurado también para usar el puerto **8000**
- Esto causaba conflictos al intentar ejecutar ambos servicios

### Solución Implementada
El servicio de imágenes ahora usa el puerto **8001** para evitar conflictos.

### Archivos Modificados

1. **`.env`**
   ```env
   API_PORT=8001
   ```

2. **`Dockerfile`**
   ```dockerfile
   EXPOSE 8001
   ```

3. **`supervisord.conf`**
   ```ini
   [program:api]
   command=uvicorn app.main:app --host 0.0.0.0 --port 8001
   ```

4. **`EASYPANEL_SETUP.md`**
   - Container Port actualizado a 8001

### Configuración de MongoDB

El archivo `.env` también incluye la configuración correcta para MongoDB:
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=serpy_db
```

**Nota**: En producción (EasyPanel), deberás ajustar `MONGODB_URI` para usar el hostname correcto del contenedor MongoDB.

### Verificación

Para verificar que el servicio está funcionando correctamente:

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Documentación API
curl http://localhost:8001/docs
```

### Puertos en Uso

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| API Principal | 8000 | Servicio API principal de Serpy |
| Images Service | 8001 | Microservicio de gestión de imágenes |
| Streamlit | 8501 | Interfaz web del scraper |

### Ejecución Local

Para ejecutar el servicio localmente:

```bash
# Construir la imagen
docker build -t serpy-images-service .

# Ejecutar el contenedor
docker run -d \
  --name serpy-images \
  -p 8001:8001 \
  -v $(pwd)/images:/images \
  --env-file .env \
  serpy-images-service
```

### Troubleshooting

Si encuentras errores de conexión a MongoDB:
1. Verifica que MongoDB esté ejecutándose
2. Ajusta `MONGODB_URI` según tu configuración local
3. Para Docker, usa el nombre del contenedor MongoDB en lugar de `localhost`
