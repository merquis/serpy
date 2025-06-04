"""
Aplicación principal del microservicio de imágenes
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
    """Gestión del ciclo de vida de la aplicación"""
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
    """Log de todas las requests"""
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
    """Maneja excepciones del servicio"""
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
    """Maneja excepciones genéricas"""
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
    """Endpoint raíz con información del servicio"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "api_docs": f"{settings.api_prefix}/docs" if settings.is_development else None,
        "health": f"{settings.api_prefix}/health",
        "metrics": f"{settings.api_prefix}/metrics",
        "endpoints": {
            "download": {
                "collection": f"{settings.api_prefix}/download/collection/{{database}}/{{collection}}",
                "document": f"{settings.api_prefix}/download/document/{{database}}/{{collection}}/{{document_id}}",
                "batch": f"{settings.api_prefix}/download/batch"
            },
            "jobs": {
                "list": f"{settings.api_prefix}/jobs",
                "get": f"{settings.api_prefix}/jobs/{{job_id}}",
                "cancel": f"{settings.api_prefix}/jobs/{{job_id}}",
                "retry": f"{settings.api_prefix}/jobs/{{job_id}}/retry"
            }
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
