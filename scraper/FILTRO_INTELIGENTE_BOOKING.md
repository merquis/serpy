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

En el archivo `scraper/services/booking_search_service.py`, se ha implementado la funcionalidad para interactuar directamente con el filtro inteligente de Booking:

- El método `search_hotels` ahora detecta si hay un filtro de lenguaje natural
- Si existe, busca y hace clic en el botón de "Filtros inteligentes"
- Localiza el textarea de filtros inteligentes usando varios selectores
- Escribe el texto del filtro en el campo
- Hace clic en "Buscar alojamientos" para aplicar el filtro
- Actualiza la URL de búsqueda con los nuevos resultados

```python
# Si hay un filtro de lenguaje natural, aplicarlo
if search_params.get('natural_language_filter'):
    # Buscar el textarea de filtros inteligentes
    textarea = await page.query_selector('textarea[autocomplete="off"]')
    if textarea:
        await textarea.type(search_params['natural_language_filter'])
        # Buscar y hacer clic en "Buscar alojamientos"
        search_button = await page.query_selector('span:has-text("Buscar alojamientos")')
        await search_button.click()
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

3. Al hacer clic en "Buscar Hoteles", el sistema:
   - Navegará a la página de resultados de Booking
   - Abrirá el panel de filtros inteligentes
   - Escribirá tu texto en el campo de filtros
   - Aplicará los filtros haciendo clic en "Buscar alojamientos"
   - Extraerá los resultados filtrados

## Notas Importantes

- **Interacción Directa**: El sistema ahora interactúa directamente con el campo de filtros inteligentes de Booking usando Playwright
- **Selectores Múltiples**: Se usan varios selectores CSS para encontrar los elementos, ya que Booking puede cambiar sus clases
- **Tiempo de Espera**: Se incluyen tiempos de espera para permitir que la página cargue los resultados después de aplicar filtros
- **Manejo de Errores**: Si no se encuentran los elementos de filtros inteligentes, el sistema continúa con la búsqueda normal

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
