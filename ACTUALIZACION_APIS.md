# Actualización de APIs - SERPY

## Fecha: 6 de Mayo de 2025

### Cambios realizados:

## 1. API Principal (api.serpsrewrite.com)

### Información actualizada en el endpoint raíz (`/`):

#### Nuevos campos añadidos:
- **usage_examples**: Ampliado con ejemplos de hoteles
  - `list_hotels`: Ejemplo de listado de hoteles
  - `search_hotels`: Ejemplo de búsqueda de hoteles en Tenerife
  - `get_hotel`: Ejemplo de obtener un hotel específico con slug

- **features**: Nueva sección que describe las características principales
  - Paginación en todos los endpoints de listado
  - Búsqueda de texto completo
  - Soporte para slugs en URLs
  - Formato JSON con indentación

- **related_services**: Nueva sección con servicios relacionados
  - Enlace al servicio de imágenes con descripción

### Información mantenida:
- Información básica del servicio (nombre, versión, descripción)
- Endpoints principales (health, collections, reload_collections)
- Listado dinámico de colecciones con sus endpoints
- Ejemplos de uso existentes

## 2. Servicio de Imágenes (images.serpsrewrite.com)

### Información actualizada en el endpoint raíz (`/`):

#### Nuevos campos añadidos:
- **description**: Descripción del servicio
- **base_url**: URL base del servicio
- **endpoints.download.from_api_url_simple**: Nuevo endpoint para descarga desde APIs externas
- **endpoints.images**: Nueva sección completa con endpoints de servir imágenes
  - `list_all`: Listar todas las imágenes
  - `list_collection`: Listar imágenes de una colección
  - `list_document`: Listar imágenes de un documento
  - `serve_image`: Servir una imagen específica

- **features**: Nueva sección describiendo todas las características
  - Descarga desde MongoDB
  - Descarga desde APIs externas
  - Descarga por lotes
  - Gestión de trabajos asíncronos
  - Servir imágenes con URLs directas
  - Listado de imágenes
  - Reintentos automáticos
  - Almacenamiento de metadatos

- **usage_examples**: Ejemplos completos de uso
  - Descarga de imágenes de hotel
  - Descarga desde API externa (con método POST y body)
  - Listado de imágenes de un hotel
  - Servir una imagen específica

- **related_services**: Enlaces a servicios relacionados
- **authentication**: Información sobre autenticación con API Key

### Información mantenida:
- Información básica del servicio
- Endpoints existentes de download y jobs
- Health y metrics endpoints

## Resumen

Ambas APIs ahora muestran información completa y actualizada en sus endpoints raíz, incluyendo:

1. **Mejor documentación**: Descripciones claras de qué hace cada servicio
2. **Ejemplos prácticos**: Casos de uso reales con URLs completas
3. **Características destacadas**: Lista de funcionalidades principales
4. **Interconexión**: Referencias cruzadas entre servicios relacionados
5. **Información de autenticación**: Detalles sobre cómo autenticarse (en el servicio de imágenes)

Esta actualización mejora significativamente la experiencia del desarrollador al proporcionar toda la información necesaria para usar las APIs directamente desde el endpoint raíz.
