# SERPY API

Microservicio FastAPI para exponer las colecciones de MongoDB de SERPY a través de una API REST.

## Características

- 🚀 API REST con FastAPI
- 📦 Acceso a colecciones MongoDB: `urls_google`, `urls_google_tags`, `hoteles`, `posts`
- 🔍 Búsqueda y paginación
- 📝 URLs amigables con slug cuando está disponible
- 🐳 Listo para Docker
- 📚 Documentación automática con Swagger/OpenAPI

## Estructura de URLs

Las URLs siguen el formato:
- `https://serpy.videocursosweb.com/{colección}/{id_mongo}-{slug}` (si existe slug)
- `https://serpy.videocursosweb.com/{colección}/{id_mongo}` (si no existe slug)

## Endpoints Disponibles

### Información General
- `GET /` - Información de la API
- `GET /health` - Estado de salud de la API
- `GET /collections` - Lista de colecciones disponibles

### Operaciones con Colecciones
- `GET /{collection}` - Lista documentos con paginación
  - Parámetros: `page`, `page_size`, `search`
- `GET /{collection}/{document_id}` - Obtiene un documento específico
- `GET /{collection}/search/{query}` - Busca documentos en una colección

## Instalación

### Requisitos
- Python 3.11+
- MongoDB

### Configuración Local

1. Clonar el repositorio y navegar al directorio:
```bash
cd api
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar credenciales:

Opción A - Usando archivo secrets.json:
```bash
cp secrets.json.example secrets.json
# Editar secrets.json con las credenciales correctas de MongoDB
```

Opción B - Usando variables de entorno:
```bash
cp .env.example .env
# Editar .env con las credenciales correctas
```

5. Ejecutar la aplicación:
```bash
python main.py
```

La API estará disponible en `http://localhost:8000`

### Usando Docker

1. Construir la imagen:
```bash
docker build -t serpy-api .
```

2. Ejecutar el contenedor:
```bash
docker run -d \
  --name serpy-api \
  -p 8000:8000 \
  -e MONGO_URI="mongodb://serpy:password@host:27017/?authSource=admin" \
  -e MONGO_DB_NAME="serpy" \
  serpy-api
```

## Documentación de la API

Cuando la aplicación está en modo desarrollo (`ENVIRONMENT=development`), la documentación interactiva está disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MONGO_URI` | URI de conexión a MongoDB | `mongodb://localhost:27017/` |
| `MONGO_DB_NAME` | Nombre de la base de datos | `serpy` |
| `API_HOST` | Host de la API | `0.0.0.0` |
| `API_PORT` | Puerto de la API | `8000` |
| `API_BASE_URL` | URL base para las URLs generadas | `https://serpy.videocursosweb.com` |
| `ENVIRONMENT` | Entorno de ejecución | `development` |

## Ejemplos de Uso

### Listar posts con paginación:
```bash
curl "http://localhost:8000/posts?page=1&page_size=10"
```

### Obtener un post específico:
```bash
curl "http://localhost:8000/posts/68407473fc91e2815c748b71-los-mejores-hoteles-lanzarote-guia-completa-2024"
```

### Buscar en una colección:
```bash
curl "http://localhost:8000/hoteles/search/lanzarote?page=1&page_size=20"
```

## Desarrollo

Para ejecutar en modo desarrollo con recarga automática:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Estructura del Proyecto

```
api/
├── main.py              # Aplicación principal FastAPI
├── config/              # Módulo de configuración
│   ├── __init__.py
│   └── settings.py      # Configuración centralizada
├── requirements.txt     # Dependencias de Python
├── Dockerfile          # Imagen Docker
├── .dockerignore       # Archivos ignorados por Docker
├── .env.example        # Ejemplo de variables de entorno
├── secrets.json.example # Ejemplo de archivo de secretos
├── .gitignore          # Archivos ignorados por Git
└── README.md           # Este archivo
