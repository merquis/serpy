# 📋 GUÍA COMPLETA DE LA INTERFAZ SERPY

## 🗂️ ESTRUCTURA GENERAL

### Archivo Principal
- **Archivo:** `streamlit_app.py`
- **Clase principal:** `SerpyApp`
- **Función de navegación:** `render_navigation_menu()`

---

## 🧭 SECCIÓN NAVEGACIÓN

### 🔍 Scraping

#### 1. **URLs de Google** (Botón Rojo)
- **Archivo UI:** `ui/pages/google_scraping.py`
- **Clase:** `GoogleScrapingPage`
- **Servicio:** `services/google_scraping_service.py`
- **Clase del servicio:** `GoogleScrapingService`
- **Función principal:** `search_multiple_queries()`
- **Función del botón:** Se ejecuta con `_perform_search()` que llama a `search_multiple_queries()`
- **Funcionalidad adicional:** 
  - **Checkbox "🏷️ Extraer etiquetas HTML automáticamente"**: Ejecuta un flujo 2 en 1
  - Cuando está marcado: busca URLs → extrae etiquetas H1/H2/H3 → guarda en MongoDB colección "hoteles"
  - Cuando NO está marcado: busca URLs → guarda en MongoDB colección "URLs Google"
  - Reutiliza la lógica y visualización de `TagScrapingPage`
- **Para llamar desde otros módulos:**
  ```python
  from services.google_scraping_service import GoogleScrapingService
  service = GoogleScrapingService()
  results = service.search_multiple_queries(queries, num_results, language_code, region_code, google_domain)
  ```

#### 2. **Etiquetas HTML**
- **Archivo UI:** `ui/pages/tag_scraping.py`
- **Clase:** `TagScrapingPage`
- **Servicio:** `services/tag_scraping_service.py`
- **Clase del servicio:** `TagScrapingService`
- **Función principal:** `scrape_tags_from_json()`
- **Función del botón:** Se ejecuta con `_process_urls()` que llama a `scrape_tags_from_json()`
- **Fuentes de datos:**
  - Desde Drive (carpeta "scraping google")
  - Desde ordenador (archivo JSON)
  - **Desde MongoDB** (colección "URLs Google") - muestra los últimos 50 documentos con ID completo
- **Para llamar desde otros módulos:**
  ```python
  from services.tag_scraping_service import TagScrapingService
  service = TagScrapingService()
  results = await service.scrape_tags_from_json(json_data, max_concurrent, progress_callback)
  ```

#### 3. **URLs manuales**
- **Archivo UI:** `ui/pages/manual_scraping.py`
- **Clase:** `ManualScrapingPage`
- **Servicio:** `services/manual_scraping_service.py`
- **Clase del servicio:** `ManualScrapingService`
- **Función principal:** `scrape_urls()`
- **Función del botón:** Se ejecuta con `_execute_scraping()` que llama a `scrape_urls()`
- **Para llamar desde otros módulos:**
  ```python
  from services.manual_scraping_service import ManualScrapingService
  service = ManualScrapingService()
  results = service.scrape_urls(urls, tags, max_workers, timeout)
  ```

#### 4. **Booking.com**
- **Archivo UI:** `ui/pages/booking_scraping.py`
- **Clase:** `BookingScrapingPage`
- **Servicio:** `services/booking_scraping_service.py`
- **Clase del servicio:** `BookingScrapingService`
- **Función principal:** `scrape_hotels()`
- **Función del botón:** Se ejecuta con `_perform_scraping()` que llama a `scrape_hotels()`
- **Para llamar desde otros módulos:**
  ```python
  from services.booking_scraping_service import BookingScrapingService
  service = BookingScrapingService()
  results = await service.scrape_hotels(booking_urls, progress_callback)
  ```

---

## 📝 SECCIÓN CONTENIDO

#### 5. **Generador de artículos**
- **Archivo UI:** `ui/pages/article_generator.py`
- **Clase:** `ArticleGeneratorPage`
- **Servicio:** `services/article_generator_service.py`
- **Clase del servicio:** `ArticleGeneratorService`
- **Función principal:** `generate_article_schema()`
- **Función del botón:** Se ejecuta con `_execute_generation()` que llama a `generate_article_schema()`
- **Para llamar desde otros módulos:**
  ```python
  from services.article_generator_service import ArticleGeneratorService
  service = ArticleGeneratorService()
  result = service.generate_article_schema(keyword, language, content_type, model, generate_text, generate_slug, competition_data, temperature, top_p, frequency_penalty, presence_penalty)
  ```

#### 6. **Chat GPT**
- **Archivo UI:** `ui/pages/gpt_chat.py`
- **Clase:** `GPTChatPage`
- **Servicio:** `services/chat_service.py`
- **Clase del servicio:** `ChatService`
- **Función principal:** `generate_response()`
- **Función del botón:** Se ejecuta automáticamente al escribir en el chat input que llama a `generate_response()`
- **Para llamar desde otros módulos:**
  ```python
  from services.chat_service import ChatService
  service = ChatService()
  response = service.generate_response(messages, model, temperature, max_tokens, stream)
  ```

---

## 📊 SECCIÓN ANÁLISIS

#### 7. **Análisis semántico**
- **Archivo UI:** `ui/pages/embeddings_analysis.py`
- **Clase:** `EmbeddingsAnalysisPage`
- **Servicio:** `services/embeddings_service.py`
- **Clase del servicio:** `EmbeddingsService`
- **Función principal:** `analyze_and_group_titles()`
- **Función del botón:** Se ejecuta con `_execute_analysis()` que llama a `analyze_and_group_titles()`
- **Para llamar desde otros módulos:**
  ```python
  from services.embeddings_service import EmbeddingsService
  service = EmbeddingsService()
  result = service.analyze_and_group_titles(data, max_titles_h2, max_titles_h3, n_clusters_h2, n_clusters_h3, model)
  ```

---

## 🔧 SERVICIOS AUXILIARES

### Servicios de utilidad:
- **Drive:** `services/drive_service.py` - `DriveService`
- **MongoDB:** `repositories/mongo_repository.py` - `MongoRepository`
- **HTTP:** `services/utils/httpx_service.py` - `HttpxService`
- **Playwright:** `services/utils/playwright_service.py` - `PlaywrightService`

### Componentes UI comunes:
- **Archivo:** `ui/components/common.py`
- **Componentes:** `Alert`, `Button`, `Card`, `LoadingSpinner`, `DataDisplay`, etc.

---

## 📋 RESUMEN DE FUNCIONES PRINCIPALES

| Botón | Función Principal | Servicio | Método |
|-------|------------------|----------|---------|
| URLs de Google | `search_multiple_queries()` | `GoogleScrapingService` | Scraping con BrightData API |
| Etiquetas HTML | `scrape_tags_from_json()` | `TagScrapingService` | Extracción de H1/H2/H3 |
| URLs manuales | `scrape_urls()` | `ManualScrapingService` | Scraping de etiquetas SEO |
| Booking.com | `scrape_hotels()` | `BookingScrapingService` | Extracción de datos de hoteles |
| Generador de artículos | `generate_article_schema()` | `ArticleGeneratorService` | Generación con GPT |
| Chat GPT | `generate_response()` | `ChatService` | Chat libre con GPT |
| Análisis semántico | `analyze_and_group_titles()` | `EmbeddingsService` | Agrupación con embeddings |

---

## 🎯 EJEMPLO DE USO DESDE OTROS MÓDULOS

```python
# Ejemplo para usar el scraping de Google desde otro módulo
from services.google_scraping_service import GoogleScrapingService

def mi_funcion_personalizada():
    service = GoogleScrapingService()
    
    # Configurar parámetros
    queries = ["hoteles Madrid", "restaurantes Barcelona"]
    num_results = 20
    language_code = "es"
    region_code = "es"
    google_domain = "google.es"
    
    # Ejecutar scraping
    results = service.search_multiple_queries(
        queries=queries,
        num_results=num_results,
        language_code=language_code,
        region_code=region_code,
        google_domain=google_domain
    )
    
    return results
```

---

## 🏗️ ARQUITECTURA Y REUTILIZACIÓN DE CÓDIGO

### Principios de diseño:
1. **DRY (Don't Repeat Yourself)**: No hay duplicación de código
2. **Separación de responsabilidades**: Lógica de negocio (servicios) separada de la UI (páginas)
3. **Reutilización de componentes**: Las páginas pueden importar y usar métodos de otras páginas

### Ejemplo de reutilización:
La página "URLs de Google" cuando tiene el checkbox marcado:
- **Lógica**: Usa `TagScrapingService.scrape_tags_from_json()` (mismo servicio que Etiquetas HTML)
- **Visualización**: Importa `TagScrapingPage` y usa su método `_display_url_result()`

```python
# En GoogleScrapingPage.__init__()
from ui.pages.tag_scraping import TagScrapingPage
self.tag_page = TagScrapingPage()

# En GoogleScrapingPage._display_url_result()
def _display_url_result(self, url_result: Dict[str, Any]):
    """Reutiliza el método de visualización de la página de etiquetas HTML"""
    self.tag_page._display_url_result(url_result)
```

### Flujos de datos entre módulos:
1. **URLs de Google → MongoDB (colección "URLs Google")**
2. **Etiquetas HTML → puede cargar desde MongoDB (colección "URLs Google")**
3. **URLs de Google con checkbox → MongoDB (colección "hoteles")**

---

## 📁 ESTRUCTURA DEL PROYECTO

```
serpy/
├── config/              # Configuración y settings
├── repositories/        # Capa de acceso a datos
├── services/           # Lógica de negocio
│   ├── utils/         # Utilidades (httpx, playwright)
│   └── ...            # Servicios específicos
├── ui/                # Interfaz de usuario
│   ├── components/    # Componentes reutilizables
│   └── pages/         # Páginas de la aplicación
├── streamlit_app.py   # Punto de entrada
├── requirements.txt   # Dependencias
└── Dockerfile        # Configuración Docker
```

Esta guía te proporciona toda la información que necesitas para entender la estructura de tu aplicación y cómo llamar a las funciones desde otros módulos.
