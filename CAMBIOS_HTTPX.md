# Cambios realizados para migrar de requests a httpx

## Resumen de cambios

### 1. **Nuevo servicio httpx_service.py**
Se ha creado un servicio completo en `services/utils/httpx_service.py` que proporciona:

- **HttpxService**: Servicio principal con capacidades asíncronas y síncronas
- **HttpxConfig**: Configuración flexible para diferentes escenarios
- **Lógica inteligente de fallback**: 
  - Comienza siempre con httpx (más rápido)
  - Si el código de estado es diferente de 200 o detecta bloqueos, marca que necesita Playwright
  - Detecta automáticamente: Cloudflare, captchas, bloqueos por bot, etc.
- **Medidas anti-bot integradas**:
  - Rotación de User-Agents
  - Delays aleatorios entre peticiones
  - Headers realistas de navegador
  - Manejo automático de cookies
  - Aceptación automática de políticas de cookies
  - Soporte para cloudscraper (bypass de Cloudflare)
- **Extracción de headers HTML** (h1, h2, h3, etc.)
- **Compatibilidad con requests**: Clase `HttpxRequests` para reemplazo directo

### 2. **Archivos modificados**

#### services/manual_scraping_service.py
- Eliminado `import requests`
- Añadido uso de `httpx_requests` 
- Actualizado manejo de excepciones para usar las de httpx
- Añadida detección de cuando se necesita Playwright

#### services/scraping_service.py
- Eliminado `import requests`
- Ambas clases (`GoogleScrapingService` y `TagScrapingService`) ahora usan `HttpxService`
- Mejorado el manejo de errores con información sobre si necesita Playwright

### 3. **requirements.txt actualizado**
- **Eliminado**: `requests==2.32.3`
- **Actualizado**: Todas las librerías a sus versiones más recientes (mayo 2025)
- **Añadido**:
  - `cloudscraper==1.2.71` - Para bypass de Cloudflare
  - `undetected-chromedriver==3.5.5` - Para casos extremos de anti-bot

### 4. **Configuraciones predefinidas**

El servicio incluye tres configuraciones listas para usar:

1. **Fast** (`create_fast_httpx_config()`):
   - Timeout: 15s
   - Delays: 0.3-1.0s
   - Sin cloudscraper

2. **Stealth** (`create_stealth_httpx_config()`):
   - Timeout: 30s
   - Delays: 1.0-3.0s
   - Cloudscraper habilitado
   - Rotación de User-Agents
   - Aceptación automática de cookies

3. **Aggressive** (`create_aggressive_httpx_config()`):
   - Timeout: 10s
   - Delays: 0.1-0.5s
   - Para sitios que no tienen protección

### 5. **Uso del servicio**

#### Uso asíncrono:
```python
from services.utils.httpx_service import HttpxService, create_stealth_httpx_config

service = HttpxService(create_stealth_httpx_config())
result, html = await service.get_html(url)

if result.get('success'):
    # Procesar HTML
    headers = service.extract_headers(html)
elif result.get('needs_playwright'):
    # Usar Playwright como fallback
    pass
```

#### Uso síncrono (reemplazo de requests):
```python
from services.utils.httpx_service import httpx_requests

# Reemplazo directo
response = httpx_requests.get(url, timeout=30)
if response.ok:
    html = response.text
```

### 6. **Ventajas de la migración**

1. **Mejor rendimiento**: httpx es más rápido que requests
2. **Soporte HTTP/2**: Mejor compatibilidad con sitios modernos
3. **Capacidades asíncronas**: Permite procesamiento concurrente eficiente
4. **Detección inteligente**: Sabe cuándo necesita Playwright
5. **Anti-bot integrado**: Medidas para evitar detección
6. **Manejo de cookies**: Automático y configurable
7. **Bypass de Cloudflare**: Con cloudscraper integrado

### 7. **Script de prueba**

Se incluye `test_httpx_service.py` para verificar el funcionamiento del servicio con pruebas de:
- Peticiones asíncronas
- Peticiones síncronas
- Extracción de headers
- Funcionamiento de cloudscraper
