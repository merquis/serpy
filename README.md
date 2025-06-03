# SERPY - Arquitectura de Microservicios

Sistema de scraping modular con múltiples microservicios.

## 🏗️ Estructura del Proyecto

```
serpy/
├── scraper/              # Microservicio principal de scraping
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── streamlit_app.py
│   └── ...
├── images/               # Microservicio de procesamiento de imágenes (en desarrollo)
│   └── README.md
├── docker-compose.yml    # Para desarrollo local
└── MICROSERVICES_COMMUNICATION.md  # Guía de comunicación entre servicios
```

## 🚀 Microservicios Actuales

### 1. Scraper (Activo)
- **URL Producción**: https://serpy.videocursosweb.com/
- **Puerto Local**: 8501
- **Tecnología**: Python, Streamlit, Playwright
- **Función**: Interfaz web para scraping de Google, Booking.com, etc.

### 2. Images (En desarrollo)
- **URL Producción**: Por definir
- **Puerto Local**: 8502
- **Tecnología**: Python, FastAPI (propuesto)
- **Función**: Procesamiento y optimización de imágenes

## 🔧 Configuración en EasyPanel

### Para el servicio Scraper:
1. **Repositorio**: https://github.com/merquis/serpy
2. **Rama**: main
3. **Ruta de compilación**: `/scraper`
4. **Dockerfile**: Automático (buscará en `/scraper/Dockerfile`)

### Para futuros servicios:
- Cada servicio será una app separada en EasyPanel
- Todos apuntan al mismo repositorio
- Diferente ruta de compilación para cada uno

## 🔗 Comunicación entre Microservicios

Los microservicios se comunican mediante HTTP REST:

### En Producción (EasyPanel):
```python
# Configurar como variable de entorno
IMAGES_SERVICE_URL=http://serpy-images.internal:8502
```

### En Desarrollo Local:
```python
# Docker Compose maneja la red interna
IMAGES_SERVICE_URL=http://images:8502
```

Ver [MICROSERVICES_COMMUNICATION.md](./MICROSERVICES_COMMUNICATION.md) para más detalles.

## 💻 Desarrollo Local

### Requisitos:
- Docker
- Docker Compose

### Ejecutar todos los servicios:
```bash
# Clonar repositorio
git clone https://github.com/merquis/serpy.git
cd serpy

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down
```

### Acceder a los servicios:
- Scraper: http://localhost:8501
- Images: http://localhost:8502 (cuando esté implementado)

## 📝 Variables de Entorno

### Scraper:
```env
STREAMLIT_SECRETS_TOML='
[mongodb]
uri = "mongodb://..."

[openai]
api_key = "sk-..."
'
```

### Images (futuro):
```env
SCRAPER_SERVICE_URL=http://scraper:8501
API_KEY=your-api-key
```

## 🚀 Despliegue

### Opción 1: EasyPanel (Recomendado)
- Crear una app para cada microservicio
- Configurar la ruta de compilación correspondiente
- Las apps se comunican mediante URLs internas

### Opción 2: VPS con Docker Compose
```bash
docker-compose up -d --build
```

## 📚 Documentación Adicional

- [Comunicación entre Microservicios](./MICROSERVICES_COMMUNICATION.md)
- [Guía de Despliegue](./DEPLOYMENT.md)

## 🤝 Contribuir

1. Fork el repositorio
2. Crea tu rama de feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request
