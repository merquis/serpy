"""
Aplicación principal del microservicio de imágenes

Este módulo implementa el servicio de gestión y descarga de imágenes para SERPY.
Proporciona endpoints para descargar imágenes desde MongoDB o APIs externas,
gestionar trabajos asíncronos y servir las imágenes descargadas.

Características principales:
- Descarga asíncrona de imágenes desde múltiples fuentes
- Sistema de trabajos con seguimiento de estado
- Servicio de imágenes con URLs directas
- Integración con MongoDB y APIs externas
- Reintentos automáticos para descargas fallidas
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core import settings, logger, setup_logging
from app.core.exceptions import ImagesServiceException
from app.api.v1 import api_router
from app.services.database import mongo_repository


# Configurar logging
setup_logging(log_level="INFO" if settings.is_production else "DEBUG")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    
    Maneja la inicialización y cierre de recursos:
    - Conexión a MongoDB al iniciar
    - Desconexión limpia al cerrar
    
    La aplicación puede funcionar sin MongoDB para descargas desde APIs externas.
    """
    # Startup
    logger.info(
        "Iniciando servicio de imágenes",
        version=settings.app_version,
        environment=settings.environment
    )
    
    # Conectar a MongoDB
    try:
        await mongo_repository.connect()
        logger.info("Conexión a MongoDB establecida")
    except Exception as e:
        logger.error("Error conectando a MongoDB", error=str(e))
        # No fallar el inicio si MongoDB no está disponible
    
    yield
    
    # Shutdown
    logger.info("Cerrando servicio de imágenes")
    
    # Desconectar de MongoDB
    try:
        await mongo_repository.disconnect()
        logger.info("Conexión a MongoDB cerrada")
    except Exception as e:
        logger.error("Error cerrando conexión a MongoDB", error=str(e))


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Microservicio de gestión de imágenes para SERPY",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware para logging detallado de todas las requests.
    
    Registra:
    - Inicio de cada request con método y path
    - Duración de procesamiento
    - Estado de respuesta
    - Errores si ocurren
    
    Añade headers de respuesta:
    - X-Request-ID: ID único de la request
    - X-Process-Time: Tiempo de procesamiento en segundos
    """
    start_time = time.time()
    
    # Generar request ID si no existe
    request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")
    
    # Log de inicio
    logger.info(
        "Request iniciada",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown"
    )
    
    # Procesar request
    try:
        response = await call_next(request)
        
        # Log de fin
        duration = time.time() - start_time
        logger.info(
            "Request completada",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=round(duration, 3)
        )
        
        # Añadir headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(duration, 3))
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "Request fallida",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration=round(duration, 3)
        )
        raise


# Manejador global de excepciones
@app.exception_handler(ImagesServiceException)
async def handle_service_exception(request: Request, exc: ImagesServiceException):
    """
    Maneja excepciones específicas del servicio de imágenes.
    
    Convierte ImagesServiceException en respuestas JSON estructuradas
    con código de error, mensaje y detalles adicionales.
    """
    logger.error(
        "Excepción del servicio",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def handle_generic_exception(request: Request, exc: Exception):
    """
    Maneja excepciones genéricas no capturadas.
    
    En desarrollo muestra detalles del error.
    En producción oculta información sensible.
    """
    logger.exception(
        "Excepción no manejada",
        error=str(exc),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Error interno del servidor",
            "details": {"error": str(exc)} if settings.is_development else {}
        }
    )


# Incluir routers
app.include_router(api_router, prefix=settings.api_prefix)


# Root endpoint
@app.get("/")
async def root():
    """
    Endpoint raíz con información completa del servicio.
    
    Proporciona:
    - Información general del servicio
    - Lista de todos los endpoints disponibles
    - Ejemplos de uso
    - Estructura de directorios y URLs
    - Integración con otros servicios
    
    Returns:
        dict: Información completa del servicio de imágenes
    """
    base_url = "https://images.serpsrewrite.com"
    
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "description": "Microservicio de gestión de imágenes para SERPY",
        "environment": settings.environment,
        "base_url": base_url,
        "api_docs": f"{base_url}{settings.api_prefix}/docs" if settings.is_development else None,
        "health": f"{base_url}{settings.api_prefix}/health",
        "metrics": f"{base_url}{settings.api_prefix}/metrics",
        "endpoints": {
            "download": {
                "collection": f"{base_url}{settings.api_prefix}/download/collection/{{database}}/{{collection}}",
                "document": f"{base_url}{settings.api_prefix}/download/document/{{database}}/{{collection}}/{{document_id}}",
                "batch": f"{base_url}{settings.api_prefix}/download/batch",
                "from_api_url_simple": f"{base_url}{settings.api_prefix}/download/from-api-url-simple"
            },
            "jobs": {
                "list": f"{base_url}{settings.api_prefix}/jobs",
                "get": f"{base_url}{settings.api_prefix}/jobs/{{job_id}}",
                "cancel": f"{base_url}{settings.api_prefix}/jobs/{{job_id}}",
                "retry": f"{base_url}{settings.api_prefix}/jobs/{{job_id}}/retry"
            },
            "images": {
                "list_all": f"{base_url}{settings.api_prefix}/images/",
                "list_collection": f"{base_url}{settings.api_prefix}/images/{{database}}/{{collection}}",
                "list_document": f"{base_url}{settings.api_prefix}/images/{{database}}/{{collection}}/{{document_id}}/",
                "serve_image": f"{base_url}{settings.api_prefix}/images/{{database}}/{{collection}}/{{document_id}}/{{filename}}"
            }
        },
        "features": {
            "download_from_mongodb": "Descarga imágenes desde documentos en MongoDB",
            "download_from_api": "Descarga imágenes desde APIs externas sin necesidad de MongoDB",
            "batch_download": "Descarga múltiples colecciones o documentos en una sola operación",
            "job_management": "Sistema de trabajos asíncronos con seguimiento de estado",
            "image_serving": "Servir imágenes descargadas con URLs directas",
            "image_listing": "Listar imágenes disponibles por base de datos, colección o documento",
            "automatic_retry": "Reintentos automáticos para descargas fallidas",
            "metadata_storage": "Almacenamiento de metadatos para cada documento descargado"
        },
        "usage_examples": {
            "download_hotel_images": f"{base_url}{settings.api_prefix}/download/document/serpy_db/hotel-booking/6840bc4e949575a0325d921b",
            "download_from_external_api": {
                "endpoint": f"{base_url}{settings.api_prefix}/download/from-api-url-simple",
                "method": "POST",
                "headers": {
                    "X-API-Key": "your-api-key-here",
                    "Content-Type": "application/json"
                },
                "body": {
                    "api_url": "https://api.serpsrewrite.com/hotel-booking/6840bc4e949575a0325d921b",
                    "database_name": "serpy_db",
                    "collection_name": "hotel-booking"
                },
                "description": "Descarga imágenes desde una API externa. Los parámetros database_name y collection_name determinan la estructura de directorios donde se guardarán las imágenes."
            },
            "list_hotel_images": {
                "url": f"{base_url}{settings.api_prefix}/images/serpy_db/hotel-booking/6840bc4e949575a0325d921b-vincci-seleccion-la-plantacion-del-sur/",
                "description": "Lista todas las imágenes disponibles para un hotel específico"
            },
            "serve_specific_image": {
                "url": f"{base_url}{settings.api_prefix}/images/serpy_db/hotel-booking/6840bc4e949575a0325d921b-vincci-seleccion-la-plantacion-del-sur/original/img_001.jpg",
                "description": "Sirve una imagen específica con la estructura: /[database]/[collection]/[mongo_id]-[hotel_name]/[subdirectory]/[filename]"
            }
        },
        "directory_structure": {
            "pattern": "/images/[database]/[collection]/[mongo_id]-[hotel_name]/original/",
            "example": "/images/serpy_db/hotel-booking/6840bc4e949575a0325d921b-vincci-seleccion-la-plantacion-del-sur/original/",
            "description": "Las imágenes se organizan por base de datos, colección, y luego por documento con su ID y nombre sanitizado"
        },
        "url_structure": {
            "pattern": "https://images.serpsrewrite.com/api/v1/images/[database]/[collection]/[mongo_id]-[hotel_name]/[subdirectory]/[filename]",
            "components": {
                "database": "Nombre de la base de datos MongoDB (ej: serpy_db)",
                "collection": "Nombre de la colección MongoDB (ej: hotel-booking, hotel-tripadvisor)",
                "mongo_id": "ID del documento en MongoDB",
                "hotel_name": "Nombre del hotel sanitizado (sin espacios ni caracteres especiales)",
                "subdirectory": "Subdirectorio de imágenes (ej: original, thumbnails)",
                "filename": "Nombre del archivo de imagen (ej: img_001.jpg)"
            }
        },
        "related_services": {
            "api_service": {
                "url": "https://api.serpsrewrite.com",
                "description": "API principal de SERPY con acceso a las colecciones de MongoDB"
            }
        },
        "authentication": {
            "method": "API Key",
            "header": "X-API-Key",
            "description": "Se requiere API key para todos los endpoints de descarga"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level="info" if settings.is_production else "debug"
    )
