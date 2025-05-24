# SERPY - Sistema de Extracción y Análisis de Contenido Web

SERPY es una aplicación web desarrollada con Streamlit que proporciona herramientas avanzadas para el scraping web, análisis de contenido y generación de artículos mediante IA.

## 🚀 Características principales

- **Scraping de Google**: Búsqueda automatizada de URLs en Google con soporte multiidioma
- **Extracción de etiquetas SEO**: Análisis de títulos, descripciones, H1, H2, H3, canonical, Open Graph
- **Scraping manual**: Procesamiento de listas de URLs personalizadas
- **Análisis de estructura**: Extracción jerárquica de contenido (H1 → H2 → H3)
- **Generación de artículos con IA**: Creación de contenido usando GPT-4
- **Chat con GPT**: Interfaz conversacional con modelos de OpenAI
- **Análisis de embeddings**: Análisis semántico de contenido
- **Integración con Google Drive**: Almacenamiento y gestión de archivos
- **Base de datos MongoDB**: Persistencia de datos y resultados

## 🛠️ Tecnologías utilizadas

- **Frontend**: Streamlit 1.45.1
- **HTTP Client**: httpx 0.28.1 (con fallback a Playwright)
- **Web Scraping**: BeautifulSoup4 4.13.4, Playwright 1.52.0
- **Anti-bot**: cloudscraper, undetected-chromedriver
- **IA**: OpenAI 1.82.0 (GPT-4)
- **Base de datos**: MongoDB (pymongo 4.13.0)
- **Análisis**: pandas 2.2.3, scikit-learn 1.6.1, spacy 3.8.7
- **OCR**: Tesseract, PyMuPDF 1.26.0

## 📋 Requisitos previos

- Python 3.12+
- MongoDB (local o remoto)
- Cuenta de OpenAI con API key
- (Opcional) Token de BrightData para scraping avanzado
- (Opcional) Credenciales de Google Drive

## 🔧 Instalación

### Opción 1: Instalación local

1. Clonar el repositorio:
```bash
git clone https://github.com/tu-usuario/serpy.git
cd serpy
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Instalar navegadores de Playwright:
```bash
playwright install
```

4. Configurar variables de entorno:
```bash
# Crear archivo .env o configurar en el sistema
OPENAI_API_KEY=tu_api_key
MONGODB_URI=mongodb://localhost:27017/
BRIGHTDATA_TOKEN=tu_token_opcional
```

5. Ejecutar la aplicación:
```bash
streamlit run streamlit_app.py
```

### Opción 2: Docker

1. Construir la imagen:
```bash
docker build -t serpy .
```

2. Ejecutar el contenedor:
```bash
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=tu_api_key \
  -e MONGODB_URI=mongodb://host.docker.internal:27017/ \
  serpy
```

## 📖 Uso

1. Acceder a `http://localhost:8501`
2. Seleccionar la herramienta deseada en el menú lateral
3. Configurar los parámetros según la tarea
4. Ejecutar y descargar los resultados

### Herramientas disponibles:

- **🔍 Google Scraping**: Búsqueda automatizada de URLs
- **🏷️ Tag Scraping**: Extracción de estructura H1-H2-H3
- **📝 Manual Scraping**: Análisis de URLs personalizadas
- **✍️ Article Generator**: Generación de contenido con IA
- **💬 GPT Chat**: Chat interactivo con GPT-4
- **📊 Embeddings Analysis**: Análisis semántico avanzado

## 🔐 Configuración

El sistema utiliza la clase `Config` en `config/settings.py` para gestionar:
- Tokens de API
- Conexiones a base de datos
- Parámetros de scraping
- Configuración de modelos de IA

## 🚦 Sistema de Scraping Inteligente

SERPY implementa un sistema de scraping en dos niveles:

1. **Nivel 1 - httpx**: Cliente HTTP rápido y eficiente
   - Headers dinámicos y rotación de User-Agent
   - Gestión inteligente de cookies
   - Reintentos automáticos con backoff exponencial

2. **Nivel 2 - Playwright**: Para sitios con JavaScript o anti-bot
   - Navegador headless automatizado
   - Ejecución de JavaScript
   - Captura de contenido dinámico

## 🔐 Configuración de Secretos en Easypanel

Para mantener los secretos seguros y seguir las mejores prácticas, SERPY utiliza variables de entorno para gestionar las credenciales y configuraciones sensibles.

### Configuración en Easypanel

1. En tu panel de Easypanel, ve a la sección "Entorno" de tu aplicación SERPY
2. Añade una variable de entorno llamada `STREAMLIT_SECRETS_TOML` 
3. Como valor, copia todo el contenido de tu archivo `secrets.toml` original

El formato debe ser similar a este ejemplo:

```
STREAMLIT_SECRETS_TOML='
[openai]
api_key = "sk-..."

[drive_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
"""
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[brightdata]
token = "..."
'
```

### Importante:
- No actives la opción "Crear archivo .env"
- Asegúrate de incluir las comillas simples al inicio y final del valor
- Después de guardar, implementa los cambios para que se apliquen

### Ejecución local (para desarrollo)

Si necesitas ejecutar la aplicación localmente durante el desarrollo:

1. Crea un directorio `.streamlit` en la raíz del proyecto
2. Dentro de él, crea un archivo `secrets.toml` con tus credenciales
3. Ejecuta el proyecto con `streamlit run streamlit_app.py`

Este archivo `.streamlit/secrets.toml` está incluido en `.gitignore` para evitar que se suba a git.

## 📁 Estructura del proyecto

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

## 🤝 Contribuir

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Autores

- **Tu Nombre** - *Trabajo inicial* - [tu-usuario](https://github.com/tu-usuario)

## 🙏 Agradecimientos

- OpenAI por proporcionar los modelos GPT
- Streamlit por el framework de aplicaciones web
- La comunidad de Python por las excelentes librerías
