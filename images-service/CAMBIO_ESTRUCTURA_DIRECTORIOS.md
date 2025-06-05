# Cambio en la Estructura de Directorios de Imágenes

## Resumen del Cambio

Se ha modificado la estructura de directorios para las imágenes descargadas, eliminando el nivel de colección redundante.

### Estructura Anterior
```
/images/serpy_db/hotel-booking/6841f939f0ed4f9b96291e55/6841f939f0ed4f9b96291e55-vincci-seleccin-la-plantacin-del-sur/original/img_001.jpg
```

### Estructura Nueva
```
/images/serpy_db/6841f939f0ed4f9b96291e55-vincci-seleccin-la-plantacin-del-sur/original/img_001.jpg
```

## URLs Afectadas

### Antes
```
https://images.serpsrewrite.com/api/v1/images/serpy_db/hotel-booking/6841f939f0ed4f9b96291e55/6841f939f0ed4f9b96291e55-vincci-seleccin-la-plantacin-del-sur/original/img_001.jpg
```

### Después
```
https://images.serpsrewrite.com/api/v1/images/serpy_db/6841f939f0ed4f9b96291e55-vincci-seleccin-la-plantacin-del-sur/original/img_001.jpg
```

## Archivos Modificados

1. **`app/core/config.py`**
   - Modificado el método `get_storage_path()` para eliminar el parámetro `collection` de la ruta

2. **`app/api/v1/endpoints/download_simple.py`**
   - Actualizada la creación de directorios para usar la nueva estructura
   - Actualizado el `storage_path` en la respuesta

3. **`app/api/v1/endpoints/serve.py`**
   - Actualizados los endpoints para servir imágenes:
     - `/{database}/{document_id}/` - Lista imágenes de un documento
     - `/{database}/{document_id}/{filename}` - Sirve una imagen específica
   - Eliminado el parámetro `collection` de las rutas

4. **`app/main.py`**
   - Actualizadas las URLs de ejemplo en la documentación del API

5. **`download-direct.py`**
   - Actualizado el script de descarga directa para usar la nueva estructura

## Ventajas del Cambio

1. **URLs más cortas y limpias**: Se elimina la redundancia del ID de MongoDB en la ruta
2. **Estructura más simple**: Menos niveles de directorios
3. **Mejor organización**: El directorio combina ID + nombre del hotel, haciendo más fácil la identificación

## Notas de Migración

Si tienes imágenes descargadas con la estructura anterior, necesitarás:

1. Mover los directorios para eliminar el nivel de colección
2. O bien, volver a descargar las imágenes con la nueva estructura

## Ejemplo de Migración Manual

```bash
# Desde la estructura antigua a la nueva
cd /images/serpy_db
for collection in */; do
    if [ -d "$collection" ]; then
        cd "$collection"
        for doc in */; do
            if [ -d "$doc" ]; then
                mv "$doc" "../$doc"
            fi
        done
        cd ..
        rmdir "$collection" 2>/dev/null
    fi
done
```

## API Endpoints Actualizados

### Listar imágenes de un documento
```
GET /api/v1/images/{database}/{document_id}/
```

### Servir una imagen específica
```
GET /api/v1/images/{database}/{document_id}/{filename}
```

### Descargar desde API externa (sin cambios)
```
POST /api/v1/download/from-api-url-simple
{
    "api_url": "https://api.serpsrewrite.com/hotel-booking",
    "collection_name": "hotel-booking"
}
