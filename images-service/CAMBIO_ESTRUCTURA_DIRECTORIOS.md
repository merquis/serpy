# Cambio en la Estructura de Directorios de Imágenes

## Resumen del Cambio

Se ha modificado la estructura de directorios para las imágenes descargadas para incluir tanto la base de datos como la colección de forma dinámica.

### Estructura Final
```
/images/[database]/[collection]/[mongo_id]-[hotel_name]/original/img_001.jpg
```

Por ejemplo:
```
/images/serpy_db/hotel-booking/6841f939f0ed4f9b96291e55-vincci-seleccin-la-plantacin-del-sur/original/img_001.jpg
```

## URLs Afectadas

### Estructura Final de URLs
```
https://images.serpsrewrite.com/api/v1/images/[database]/[collection]/[mongo_id]-[hotel_name]/original/img_001.jpg
```

Por ejemplo:
```
https://images.serpsrewrite.com/api/v1/images/serpy_db/hotel-booking/6841f939f0ed4f9b96291e55-vincci-seleccin-la-plantacin-del-sur/original/img_001.jpg
```

## Archivos Modificados

1. **`app/core/config.py`**
   - El método `get_storage_path()` ahora incluye database y collection en la ruta

2. **`app/api/v1/endpoints/download_simple.py`**
   - Añadido parámetro `database_name` al endpoint
   - Actualizada la creación de directorios para usar database y collection dinámicamente
   - Actualizado el `storage_path` en la respuesta

3. **`app/api/v1/endpoints/serve.py`**
   - Actualizados los endpoints para incluir collection:
     - `/{database}/{collection}/{document_id}/` - Lista imágenes de un documento
     - `/{database}/{collection}/{document_id}/{filename}` - Sirve una imagen específica

4. **`app/main.py`**
   - Actualizadas las URLs de ejemplo en la documentación del API
   - Añadido `database_name` en el ejemplo de body para el endpoint

5. **`download-direct.py`**
   - Actualizado para aceptar database_name y collection_name como parámetros
   - Usa la nueva estructura de directorios

## Ventajas del Cambio

1. **Estructura dinámica**: Soporta múltiples bases de datos y colecciones
2. **Mejor organización**: Separación clara por base de datos y colección
3. **Flexibilidad**: Permite organizar imágenes de diferentes fuentes (booking, tripadvisor, etc.)
4. **URLs descriptivas**: Incluyen toda la información necesaria para identificar el origen

## Parámetros del API

### Endpoint de descarga simplificada

```
POST /api/v1/download/from-api-url-simple
```

Parámetros:
- `api_url` (requerido): URL de la API externa con los datos
- `database_name` (opcional): Nombre de la base de datos (por defecto: "serpy_db")
- `collection_name` (opcional): Nombre de la colección (se extrae de la URL si no se proporciona)

Ejemplo de petición:
```json
{
    "api_url": "https://api.serpsrewrite.com/hotel-booking",
    "database_name": "serpy_db",
    "collection_name": "hotel-booking"
}
```

## API Endpoints Actualizados

### Listar imágenes de un documento
```
GET /api/v1/images/{database}/{collection}/{document_id}/
```

### Servir una imagen específica
```
GET /api/v1/images/{database}/{collection}/{document_id}/{filename}
```

### Listar imágenes de una colección
```
GET /api/v1/images/{database}/{collection}
```

### Descargar desde API externa
```
POST /api/v1/download/from-api-url-simple
{
    "api_url": "https://api.serpsrewrite.com/hotel-booking",
    "database_name": "serpy_db",
    "collection_name": "hotel-booking"
}
```

## Uso en Booking Scraper

Cuando se suben datos desde el scraper de Booking a MongoDB, el sistema ya conoce:
- **Base de datos**: Típicamente "serpy_db"
- **Colección**: Por ejemplo "hotel-booking", "hotel-tripadvisor", etc.

Esto permite que las imágenes se organicen automáticamente según su origen, facilitando la gestión y búsqueda posterior.

## Ejemplos de URLs por Fuente

### Booking.com
```
https://images.serpsrewrite.com/api/v1/images/serpy_db/hotel-booking/[id]-[nombre]/original/img_001.jpg
```

### TripAdvisor (futuro)
```
https://images.serpsrewrite.com/api/v1/images/serpy_db/hotel-tripadvisor/[id]-[nombre]/original/img_001.jpg
```

### Otras fuentes
```
https://images.serpsrewrite.com/api/v1/images/serpy_db/[collection-name]/[id]-[nombre]/original/img_001.jpg
