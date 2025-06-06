# Filtro Inteligente de Lenguaje Natural para Booking.com

## Descripción

Se ha añadido un nuevo campo de entrada de texto en la interfaz de búsqueda de Booking que permite escribir filtros en lenguaje natural, similar a la funcionalidad de "Filtros inteligentes" que ofrece Booking.com.

## Implementación

### 1. Interfaz de Usuario (UI)

En el archivo `scraper/ui/pages/booking_search.py`, se ha añadido un textarea en la sección de filtros:

```python
# Filtro inteligente de lenguaje natural
st.markdown("### 🤖 Filtros inteligentes")
params['natural_language_filter'] = st.text_area(
    "¿Qué estás buscando?",
    placeholder="Escribe en lenguaje natural lo que buscas, por ejemplo: '1 y 2 estrellas', 'hoteles con piscina', 'cerca de la playa', etc.",
    height=80,
    help="Este texto se transferirá al filtro inteligente de Booking.com"
)
```

### 2. Servicio de Búsqueda

En el archivo `scraper/services/booking_search_service.py`, se ha modificado el método `build_search_url` para incluir el parámetro del filtro de lenguaje natural:

```python
# Añadir filtro de lenguaje natural si existe
if params.get('natural_language_filter'):
    # El filtro inteligente de Booking podría usar un parámetro como 'nflt_query' o similar
    # Por ahora lo añadimos como parámetro de búsqueda adicional
    query_params['nflt_query'] = params.get('natural_language_filter')
```

## Uso

1. En la página de "Búsqueda Booking" de la interfaz, aparecerá un nuevo campo de texto bajo "Filtros inteligentes"
2. Escribe en lenguaje natural lo que buscas, por ejemplo:
   - "1 y 2 estrellas"
   - "hoteles con piscina"
   - "cerca de la playa"
   - "con desayuno incluido"
   - "pet friendly"
   - "con parking gratuito"

3. El texto se incluirá en la URL de búsqueda como parámetro `nflt_query`

## Notas Importantes

- **Estado Experimental**: El parámetro `nflt_query` es una aproximación. Booking.com podría usar un mecanismo diferente para sus filtros inteligentes.
- **Posibles Ajustes**: Si el parámetro actual no funciona correctamente, puede ser necesario:
  1. Investigar el parámetro exacto que usa Booking
  2. Implementar una lógica de conversión de lenguaje natural a filtros específicos
  3. Usar técnicas de web scraping más avanzadas para interactuar directamente con el campo de filtros inteligentes

## Ejemplos de Filtros

### Filtros de Categoría
- "hoteles de 3 estrellas"
- "1 y 2 estrellas"
- "hoteles de lujo"

### Filtros de Servicios
- "con piscina"
- "spa y wellness"
- "gimnasio"
- "wifi gratis"

### Filtros de Ubicación
- "cerca de la playa"
- "en el centro"
- "cerca del aeropuerto"

### Filtros de Régimen
- "todo incluido"
- "con desayuno"
- "media pensión"

### Otros Filtros
- "admite mascotas"
- "parking gratuito"
- "acceso para discapacitados"

## Próximos Pasos

1. Probar el funcionamiento con diferentes tipos de filtros
2. Analizar las URLs generadas por Booking cuando se usan sus filtros inteligentes
3. Ajustar el parámetro o implementar lógica adicional según sea necesario
