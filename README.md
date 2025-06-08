# SERPY - Sistema de Scraping y Análisis SEO

SERPY es una suite completa de herramientas SEO que incluye scraping web, gestión de imágenes y análisis de contenido. El proyecto está compuesto por tres microservicios principales que trabajan de forma integrada.

## 🏗️ Arquitectura

El proyecto está organizado en tres componentes principales:

### 1. API Principal (`/api`)
API REST que proporciona acceso a las colecciones de MongoDB con detección dinámica de colecciones.

**Características:**
- Detección automática de colecciones desde MongoDB
- Endpoints RESTful para cada colección
- Búsqueda de texto completo
- Paginación configurable
- URLs amigables con slugs opcionales
- Respuestas JSON formateadas

**Tecnologías:**
- FastAPI
- MongoDB (PyMongo)
- Python 3.8+

### 2. Servicio de Imágenes (`/images-service`)
Microservicio especializado en la descarga y gestión de imágenes.

**Características:**
- Descarga asíncrona de imágenes desde MongoDB o APIs externas
- Sistema de trabajos con seguimiento de estado
- Servicio de imágenes con URLs directas
- Reintentos automáticos para descargas fallidas
- Organización estructurada de archivos

**Tecnologías:**
- FastAPI
- Celery + Redis (para trabajos asíncronos)
- httpx (para descargas asíncronas)
- MongoDB (opcional)

### 3. Scraper (`/scraper`)
Interfaz web para scraping y análisis de contenido.

**Características:**
- Scraping de resultados de Google
- Extracción de datos de Booking.com
- Generación de artículos con GPT
- Análisis semántico con embeddings
- Integración con Google Drive

**Tecnologías:**
- Streamlit
- Selenium/Playwright
- OpenAI API
- Google Drive API

## 🚀 Instalación y Configuración

### Requisitos Previos
- Docker y Docker Compose
- Python 3.8+
- MongoDB
- Redis (para el servicio de imágenes)

### Configuración Rápida

1. **Clonar el repositorio:**
```bash
git clone https://github.com/serpy/serpy.git
cd serpy
```

2. **Configurar variables de entorno:**

Para la API:
```bash
cp api/.env.example api/.env
# Editar api/.env con tus credenciales
```

Para el servicio de imágenes:
```bash
cp images-service/.env.example images-service/.env
# Editar images-service/.env
```

3. **Iniciar con Docker Compose:**
```bash
docker-compose up -d
```

## 📚 Documentación de APIs

### API Principal
- **URL Base:** https://api.serpsrewrite.com
- **Documentación:** https://api.serpsrewrite.com/docs (en desarrollo)

#### Endpoints principales:
- `GET /` - Información de la API y colecciones disponibles
- `GET /health` - Estado de salud de la API
- `GET /collections` - Lista de colecciones
- `GET /{collection}` - Listar documentos con paginación
- `GET /{collection}/{id}` - Obtener documento específico
- `GET /{collection}/search/{query}` - Buscar en colección

### Servicio de Imágenes
- **URL Base:** https://images.serpsrewrite.com
- **Autenticación:** Header `X-API-Key`

#### Endpoints principales:
- `POST /api/v1/download/from-api-url-simple` - Descargar desde API externa
- `GET /api/v1/jobs` - Listar trabajos de descarga
- `GET /api/v1/images/{database}/{collection}/{document_id}/` - Listar imágenes
- `GET /api/v1/images/{database}/{collection}/{document_id}/{filename}` - Servir imagen

## 🔧 Desarrollo

### Estructura del Proyecto
```
serpy/
├── api/                    # API principal
│   ├── main.py            # Aplicación FastAPI
│   ├── config/            # Configuración
│   └── requirements.txt   # Dependencias
│
├── images-service/        # Servicio de imágenes
│   ├── app/              # Código de la aplicación
│   │   ├── api/          # Endpoints
│   │   ├── core/         # Configuración y utilidades
│   │   ├── models/       # Modelos de datos
│   │   ├── services/     # Lógica de negocio
│   │   └── workers/      # Trabajos asíncronos
│   └── requirements.txt
│
└── scraper/              # Interfaz de scraping
    ├── streamlit_app.py  # Aplicación principal
    ├── config/           # Configuración
    ├── services/         # Servicios de scraping
    └── ui/               # Componentes de UI
```

### Ejecutar en Desarrollo

**API Principal:**
```bash
cd api
pip install -r requirements.txt
python main.py
```

**Servicio de Imágenes:**
```bash
cd images-service
pip install -r requirements.txt
# Terminal 1: API
python -m app.main
# Terminal 2: Worker Celery
celery -A app.workers.celery_app worker --loglevel=info
```

**Scraper:**
```bash
cd scraper
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 🔐 Seguridad

- Todas las APIs requieren autenticación mediante API Key
- Las credenciales sensibles se almacenan en archivos `.env` o `secrets.json`
- CORS configurado para dominios específicos en producción
- Logs sanitizados para no exponer información sensible

## 📊 Monitoreo

- Logs estructurados en formato JSON
- Métricas de rendimiento en cada request
- Health checks para cada servicio
- Sistema de alertas para errores críticos

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es privado y propietario. Todos los derechos reservados.

## 👥 Equipo

- **Desarrollo:** Equipo SERPY
- **Contacto:** contacto@serpsrewrite.com

---

Para más información, consulta la documentación específica de cada componente en sus respectivos directorios.
