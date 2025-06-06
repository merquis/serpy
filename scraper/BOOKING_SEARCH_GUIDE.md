# Guía de Búsqueda en Booking.com

## Descripción General

El nuevo sistema de búsqueda de Booking permite realizar búsquedas parametrizadas en Booking.com y extraer información de los hoteles encontrados. A diferencia del scraper de URLs individuales, este sistema:

1. **Genera URLs de búsqueda** basadas en parámetros seleccionados
2. **Extrae resultados de búsqueda** con información básica de cada hotel
3. **Permite procesar los hoteles encontrados** con el scraper detallado

## Características Principales

### 1. Parámetros de Búsqueda

#### Destino y Tipo
- **Destino**: Ciudad, región o lugar (ej: "Tenerife", "Madrid", "Costa del Sol")
- **Tipo de destino**: region, city, hotel

#### Fechas
- **Check-in**: Fecha de entrada al hotel
- **Check-out**: Fecha de salida del hotel

#### Ocupación
- **Adultos**: Número de adultos (1-30)
- **Niños**: Número de niños (0-10)
- **Habitaciones**: Número de habitaciones (1-30)
- **Edades de niños**: Si hay niños, especificar edad de cada uno

#### Filtros
- **Categoría (estrellas)**: Selección múltiple (1-5 estrellas)
- **Puntuación mínima**: Sin filtro, 7.0, 8.0, 9.0
- **Régimen alimenticio**:
  - Desayuno incluido
  - Media pensión
  - Todo incluido
  - Desayuno buffet

#### Control de Resultados
- **Número máximo de hoteles**: Entre 5 y 50 hoteles

### 2. Información Extraída

Para cada hotel encontrado se extrae:
- **Nombre del hotel**
- **URL del hotel** (para procesamiento detallado)
- **Puntuación** (rating)
- **Número de reseñas**
- **Precio** (precio más bajo encontrado)
- **Ubicación**
- **Imagen principal**
- **Tipo de propiedad** (hotel, apartamento, etc.)

### 3. Flujo de Trabajo

1. **Configurar parámetros** en la interfaz
2. **Ver URL generada** (opcional) para verificar los parámetros
3. **Ejecutar búsqueda** - El sistema navega a Booking y extrae resultados
4. **Revisar resultados** - Ver hoteles encontrados
5. **Exportar o procesar**:
   - Descargar JSON con resultados
   - Subir a Google Drive
   - Procesar hoteles con el scraper detallado

## Ejemplo de URL Generada

```
https://www.booking.com/searchresults.es.html?
dest_type=region&
dest_id=13444&
checkin=2025-06-20&
checkout=2025-06-25&
group_adults=2&
group_children=1&
age=5&
no_rooms=1&
nflt=class%3D4%3Bclass%3D5%3Breview_score%3D90%3Bmealplan%3D3
```

## Parámetros de URL de Booking

### Parámetros Básicos
- `ss`: Término de búsqueda
- `dest_type`: Tipo de destino (region, city, hotel)
- `dest_id`: ID interno del destino
- `checkin/checkout`: Fechas en formato YYYY-MM-DD
- `group_adults/children`: Número de adultos/niños
- `age`: Edades de los niños
- `no_rooms`: Número de habitaciones

### Filtros (nflt)
- `class=X`: Categoría de estrellas (1-5)
- `review_score=X0`: Puntuación mínima (70, 80, 90)
- `mealplan=X`: Régimen (1=desayuno, 3=todo incluido, 4=media pensión)
- `ht_id=204`: Tipo de alojamiento
- `hotelfacility=X`: Instalaciones del hotel
- `roomfacility=X`: Facilidades de habitación

## Integración con el Scraper Detallado

Una vez obtenidos los resultados de búsqueda:

1. Click en **"Procesar Hoteles"**
2. Las URLs se copian automáticamente
3. Ir a la página **"Booking.com"** (scraper detallado)
4. Las URLs estarán pre-cargadas
5. Ejecutar el scraping detallado para obtener toda la información

## Notas Técnicas

- Utiliza **rebrowser_playwright** para evitar detección
- Maneja popups y elementos dinámicos automáticamente
- Los selectores están preparados para cambios en la estructura de Booking
- Incluye reintentos y manejo de errores

## Limitaciones

- Booking puede cambiar su estructura HTML sin previo aviso
- Los resultados pueden variar según la ubicación del servidor
- Respetar los términos de servicio de Booking.com
- El número de resultados puede ser menor al solicitado si no hay suficientes hoteles
