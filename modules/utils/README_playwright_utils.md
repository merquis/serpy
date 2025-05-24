# 🎭 Módulo Reutilizable de Playwright

Este módulo (`playwright_utils.py`) proporciona funciones genéricas para capturar HTML usando Playwright, diseñado para ser reutilizado por diferentes scrapers sin duplicar código.

## 📋 Características

- **Configuración flexible**: Personaliza timeouts, selectores de espera, headers, etc.
- **Manejo de errores robusto**: Gestión consistente de errores y timeouts
- **Procesamiento en lote**: Capacidad para procesar múltiples URLs concurrentemente
- **Fácil integración**: API simple para usar en cualquier scraper

## 🚀 Uso Básico

### 1. Importar el módulo

```python
from modules.utils.playwright_utils import (
    PlaywrightConfig,
    obtener_html_simple,
    procesar_urls_en_lote,
    crear_config_booking,
    crear_config_generica
)
```

### 2. Obtener HTML de una URL

```python
import asyncio
from modules.utils.playwright_utils import obtener_html_simple

async def mi_scraper():
    # Obtener HTML con configuración por defecto
    resultado, html = await obtener_html_simple("https://example.com")
    
    if resultado.get("error"):
        print(f"Error: {resultado['error']}")
    else:
        print(f"HTML obtenido: {len(html)} caracteres")
        # Procesar el HTML con BeautifulSoup...

# Ejecutar
asyncio.run(mi_scraper())
```

### 3. Configuración personalizada

```python
from modules.utils.playwright_utils import PlaywrightConfig, obtener_html_simple

# Crear configuración personalizada
config = PlaywrightConfig(
    wait_for_selector=".content-loaded",  # Esperar a que aparezca este selector
    timeout=45000,  # 45 segundos de timeout
    wait_until="networkidle",  # Esperar a que no haya actividad de red
    user_agent="Mi Bot Personalizado/1.0",
    extra_headers={
        "Accept-Language": "es-ES",
        "Custom-Header": "valor"
    }
)

resultado, html = await obtener_html_simple("https://example.com", config)
```

### 4. Procesar múltiples URLs

```python
urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3"
]

# Procesar con máximo 3 páginas concurrentes
resultados = await procesar_urls_en_lote(urls, config, max_concurrent=3)

for resultado, html in resultados:
    if resultado.get("error"):
        print(f"Error en {resultado['url_original']}: {resultado['error']}")
    else:
        print(f"Éxito en {resultado['url_original']}: {len(html)} caracteres")
```

## 📖 API Reference

### `PlaywrightConfig`

Clase de configuración con los siguientes parámetros:

- `headless` (bool): Ejecutar en modo sin ventana. Default: `True`
- `timeout` (int): Timeout para cargar la página en ms. Default: `60000`
- `wait_until` (str): Evento a esperar. Opciones: `"load"`, `"domcontentloaded"`, `"networkidle"`. Default: `"networkidle"`
- `user_agent` (str): User-Agent personalizado
- `accept_language` (str): Header Accept-Language. Default: `"es-ES,es;q=0.9,en;q=0.8"`
- `ignore_https_errors` (bool): Ignorar errores HTTPS. Default: `True`
- `wait_for_selector` (str): Selector CSS a esperar antes de capturar HTML
- `wait_for_timeout` (int): Timeout para wait_for_selector en ms. Default: `15000`
- `extra_headers` (dict): Headers HTTP adicionales

### Funciones principales

#### `obtener_html_simple(url, config=None)`
Obtiene HTML de una sola URL.

**Returns**: `Tuple[Dict, str]` - (resultado_dict, html_content)

#### `procesar_urls_en_lote(urls, config=None, max_concurrent=5)`
Procesa múltiples URLs en lote.

**Returns**: `List[Tuple[Dict, str]]` - Lista de tuplas (resultado_dict, html_content)

#### `obtener_html_con_playwright(url, browser_instance, config=None)`
Función de bajo nivel que requiere una instancia de browser existente.

### Funciones helper

#### `crear_config_booking()`
Crea una configuración optimizada para Booking.com

#### `crear_config_generica(wait_for_selector=None, timeout=30000)`
Crea una configuración genérica personalizable

## 🔧 Ejemplos de Integración

### Ejemplo 1: Scraper de Booking (ya implementado)

```python
# En scraping_booking.py
from modules.utils.playwright_utils import crear_config_booking, obtener_html_simple

async def obtener_datos_booking(url):
    config = crear_config_booking()
    resultado, html = await obtener_html_simple(url, config)
    
    if not resultado.get("error"):
        soup = BeautifulSoup(html, "html.parser")
        # Parsear datos específicos de Booking...
```

### Ejemplo 2: Scraper de e-commerce

```python
from modules.utils.playwright_utils import PlaywrightConfig, procesar_urls_en_lote

async def scrapear_productos(urls_productos):
    # Configuración para esperar a que los precios se carguen
    config = PlaywrightConfig(
        wait_for_selector=".price-tag",
        wait_until="networkidle",
        timeout=30000
    )
    
    resultados = await procesar_urls_en_lote(urls_productos, config)
    
    productos = []
    for resultado, html in resultados:
        if not resultado.get("error"):
            soup = BeautifulSoup(html, "html.parser")
            # Extraer información del producto...
            productos.append(extraer_datos_producto(soup))
    
    return productos
```

### Ejemplo 3: Scraper de noticias

```python
async def scrapear_articulo_noticia(url):
    # Configuración rápida para sitios de noticias
    config = PlaywrightConfig(
        wait_until="domcontentloaded",  # No esperar a todas las imágenes
        timeout=20000,
        wait_for_selector="article"  # Esperar al contenido principal
    )
    
    resultado, html = await obtener_html_simple(url, config)
    # Procesar artículo...
```

## 🐛 Manejo de Errores

El módulo retorna errores estructurados:

```python
{
    "error": "Tipo_De_Error",
    "url_original": "https://example.com",
    "details": "Descripción detallada del error"
}
```

Tipos de error comunes:
- `HTML_Vacio`: No se obtuvo contenido HTML
- `Timeout_Playwright`: Timeout al cargar la página
- `Excepcion_Playwright_[Tipo]`: Excepción específica de Playwright
- `Excepcion_Gather`: Error al procesar en lote
- `Resultado_Inesperado`: Resultado no esperado

## 💡 Mejores Prácticas

1. **Usa configuraciones específicas**: Crea configuraciones adaptadas a cada sitio web
2. **Maneja los errores**: Siempre verifica si hay errores antes de procesar el HTML
3. **Limita la concurrencia**: No uses más de 5-10 páginas concurrentes
4. **Optimiza los selectores**: Usa selectores específicos para reducir tiempos de espera
5. **Considera el modo headless**: Usa `headless=True` para mejor rendimiento

## 📝 Notas

- El módulo usa Chromium por defecto
- Asegúrate de tener Playwright instalado: `pip install playwright`
- Instala los navegadores: `playwright install chromium`
