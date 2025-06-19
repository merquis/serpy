# SerializeGetEngine - Servicio de Serialización para JetEngine

## Descripción

`SerializeGetEngine` es un servicio independiente y reutilizable que proporciona funciones de serialización PHP para estructuras de datos complejas, especialmente diseñado para trabajar con JetEngine de WordPress.

## Características

- ✅ Serialización de bloques H2 con contenido
- ✅ Serialización de campos personalizados genéricos
- ✅ Serialización de campos repetidores
- ✅ Serialización de galerías de imágenes
- ✅ Serialización completa de campos meta
- ✅ Deserialización de datos PHP
- ✅ Validación de datos serializados
- ✅ Funciones de conveniencia para uso directo

## Instalación

El servicio requiere la librería `phpserialize`:

```bash
pip install phpserialize
```

## Uso Básico

### Importar el servicio

```python
from services.serialice_get_engine import SerializeGetEngine

# O usar las funciones de conveniencia
from services.serialice_get_engine import serialize_h2_blocks, serialize_custom_fields
```

### 1. Serializar Bloques H2

```python
h2_sections = [
    {
        "titulo": "Ubicación privilegiada",
        "contenido": "Este hotel se encuentra en el corazón de la ciudad."
    },
    {
        "titulo": "Servicios destacados", 
        "contenido": "<h3>Spa</h3>Tratamientos relajantes disponibles."
    }
]

# Usando la clase
resultado = SerializeGetEngine.serialize_h2_blocks(h2_sections)

# Usando función de conveniencia
resultado = serialize_h2_blocks(h2_sections)

# Resultado: {"bloques_contenido_h2": "a:2:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:21:\"Ubicación privilegiada\";s:10:\"parrafo_h2\";s:58:\"<p>Este hotel se encuentra en el corazón de la ciudad.</p>\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:20:\"Servicios destacados\";s:10:\"parrafo_h2\";s:49:\"<h3>Spa</h3>Tratamientos relajantes disponibles.\n\";}}"}
```

### 2. Serializar Campos Personalizados

```python
datos = {
    "servicios": ["WiFi", "Piscina", "Spa"],
    "valoraciones": {"limpieza": 9.2, "ubicacion": 8.8},
    "precio": "150.00"
}

# Con mapeo de campos opcional
mapeo = {"precio": "precio_noche"}

resultado = SerializeGetEngine.serialize_custom_fields(datos, mapeo)
```

### 3. Serializar Campo Repetidor

```python
servicios = [
    {"nombre": "WiFi gratuito", "descripcion": "Internet de alta velocidad"},
    {"nombre": "Piscina", "descripcion": "Piscina climatizada 24h"}
]

resultado = SerializeGetEngine.serialize_repeater_field(servicios, "servicio")
# Resultado: {"servicio_repeater": "...datos serializados..."}
```

### 4. Serializar Galería de Imágenes

```python
imagenes = [
    {
        "image_url": "https://example.com/img1.jpg",
        "title": "Imagen 1",
        "alt_text": "Descripción imagen 1",
        "caption": "Caption 1",
        "description": "Descripción completa",
        "filename": "img1.jpg"
    }
]

resultado = SerializeGetEngine.serialize_gallery_field(imagenes, "galeria_hotel")
```

### 5. Serializar Todos los Campos Meta

```python
meta_data = {
    "nombre_alojamiento": "Hotel Ejemplo",
    "frases_destacadas": [
        {"frase_destacada": "Ubicación excepcional"},
        {"frase_destacada": "Servicio de primera"}
    ],
    "servicios": ["WiFi", "Piscina"],
    "images": [...],  # Lista de imágenes
    "valoraciones": {"limpieza": 9.2}
}

resultado = SerializeGetEngine.serialize_meta_fields(meta_data)
```

### 6. Deserializar Datos

```python
# Deserializar datos PHP serializados
datos_deserializados = SerializeGetEngine.deserialize_php_field(datos_serializados)

# Validar si los datos están correctamente serializados
es_valido = SerializeGetEngine.validate_serialized_data(datos_serializados)
```

## Métodos Disponibles

### Métodos Estáticos de la Clase

| Método | Descripción |
|--------|-------------|
| `serialize_h2_blocks(h2_sections)` | Serializa bloques H2 con contenido |
| `serialize_custom_fields(data, field_mapping=None)` | Serializa campos personalizados genéricos |
| `serialize_repeater_field(items, field_prefix="item")` | Serializa campo repetidor |
| `serialize_gallery_field(images, field_name="gallery")` | Serializa galería de imágenes |
| `serialize_meta_fields(meta_data)` | Serializa todos los campos meta |
| `deserialize_php_field(serialized_data)` | Deserializa datos PHP |
| `validate_serialized_data(serialized_data)` | Valida datos serializados |

### Funciones de Conveniencia

```python
from services.serialice_get_engine import (
    serialize_h2_blocks,
    serialize_custom_fields,
    serialize_repeater_field,
    serialize_gallery_field,
    serialize_meta_fields
)
```

## Integración con Booking Service

El servicio ya está integrado en `booking_extraer_datos_service.py`:

```python
from services.serialice_get_engine import SerializeGetEngine

# En lugar de la función anterior _build_h2_flat_structure
def _build_h2_flat_structure(self, h2_sections):
    return SerializeGetEngine.serialize_h2_blocks(h2_sections)
```

## Casos de Uso

### 1. Desde un Servicio de Scraping

```python
from services.serialice_get_engine import SerializeGetEngine

class MiScrapingService:
    def procesar_datos(self, datos_extraidos):
        # Serializar H2 extraídos
        h2_serializado = SerializeGetEngine.serialize_h2_blocks(datos_extraidos['h2_sections'])
        
        # Serializar servicios como repetidor
        servicios_serializado = SerializeGetEngine.serialize_repeater_field(
            [{"servicio": s} for s in datos_extraidos['servicios']], 
            "servicio"
        )
        
        return {**h2_serializado, **servicios_serializado}
```

### 2. Desde una API

```python
from services.serialice_get_engine import serialize_meta_fields

def crear_post_wordpress(datos_hotel):
    # Serializar todos los campos meta
    meta_serializado = serialize_meta_fields(datos_hotel['meta'])
    
    return {
        "title": datos_hotel['title'],
        "content": datos_hotel['content'],
        "meta": meta_serializado
    }
```

### 3. Procesamiento de Datos Existentes

```python
from services.serialice_get_engine import SerializeGetEngine

def migrar_datos_antiguos(datos_antiguos):
    # Convertir datos antiguos al nuevo formato serializado
    if 'h2_sections' in datos_antiguos:
        datos_antiguos['bloques_contenido_h2'] = SerializeGetEngine.serialize_h2_blocks(
            datos_antiguos['h2_sections']
        )
    
    return datos_antiguos
```

## Ventajas del Servicio Independiente

1. **Reutilización**: Se puede usar desde cualquier archivo o servicio
2. **Mantenibilidad**: Código centralizado para serialización
3. **Consistencia**: Mismo formato de serialización en toda la aplicación
4. **Testabilidad**: Fácil de probar de forma aislada
5. **Extensibilidad**: Fácil añadir nuevos tipos de serialización

## Logging

El servicio incluye logging detallado:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Los logs mostrarán información sobre:
# - Número de elementos serializados
# - Errores en la serialización
# - Validaciones de datos
```

## Ejemplo Completo

Ver el archivo `ejemplo_uso_serialice_get_engine.py` para ejemplos completos de uso.

## Notas Técnicas

- Utiliza la librería `phpserialize` para compatibilidad total con PHP
- Maneja automáticamente la conversión de bytes a string
- Procesa contenido HTML manteniendo las etiquetas necesarias
- Incluye validación de datos antes de la serialización
- Manejo robusto de errores con logging detallado

## Migración desde el Código Anterior

Si tienes código que usa la función anterior `_build_h2_flat_structure`, simplemente reemplázala:

```python
# Antes
resultado = self._build_h2_flat_structure(h2_sections)

# Después
from services.serialice_get_engine import SerializeGetEngine
resultado = SerializeGetEngine.serialize_h2_blocks(h2_sections)
