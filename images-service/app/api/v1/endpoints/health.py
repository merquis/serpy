"""
Endpoints de health check y métricas
"""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import psutil
import time

from app.core import settings, logger
from app.models.schemas import HealthResponse
from app.services.database import mongo_repository
from app.services.storage import LocalStorageService
from app.api.v1.dependencies import optional_api_key


router = APIRouter(tags=["monitoring"])

# Métricas de Prometheus
images_downloaded = Counter(
    'images_downloaded_total',
    'Total number of images downloaded',
    ['status', 'collection']
)

download_duration = Histogram(
    'download_duration_seconds',
    'Time spent downloading images',
    ['collection']
)

active_jobs = Gauge(
    'active_jobs',
    'Number of active download jobs',
    ['type', 'status']
)

storage_usage = Gauge(
    'storage_usage_bytes',
    'Storage space used for images'
)


@router.get("/health", response_model=HealthResponse)
async def health_check(api_key: str = Depends(optional_api_key)):
    """
    Health check del servicio
    
    Returns:
        Estado del servicio y sus componentes
    """
    health_status = {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }
    
    # Verificar MongoDB
    try:
        await mongo_repository.connect()
        # Hacer ping para verificar conexión
        await mongo_repository._client.admin.command('ping')
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = f"error: {str(e)}"
        logger.error("MongoDB health check failed", error=str(e))
    
    # Verificar Redis (a través de Celery)
    try:
        from app.workers import celery_app
        # Inspeccionar workers activos
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        if stats:
            health_status["redis"] = "connected"
            health_status["celery_workers"] = len(stats)
        else:
            health_status["redis"] = "connected"
            health_status["celery_workers"] = 0
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["redis"] = f"error: {str(e)}"
        logger.error("Redis/Celery health check failed", error=str(e))
    
    # Verificar almacenamiento
    try:
        storage = LocalStorageService()
        storage_stats = await storage.get_storage_stats()
        health_status["storage"] = storage_stats
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["storage"] = {"error": str(e)}
        logger.error("Storage health check failed", error=str(e))
    
    # Información del sistema
    try:
        health_status["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
    except Exception as e:
        logger.warning("System stats failed", error=str(e))
    
    return HealthResponse(**health_status)


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics(api_key: str = Depends(optional_api_key)):
    """
    Métricas en formato Prometheus
    
    Returns:
        Métricas del servicio
    """
    try:
        # Actualizar métricas de jobs activos
        await update_job_metrics()
        
        # Actualizar métricas de almacenamiento
        await update_storage_metrics()
        
        # Generar métricas
        metrics_data = generate_latest()
        
        return PlainTextResponse(
            content=metrics_data.decode('utf-8'),
            media_type="text/plain; version=0.0.4"
        )
        
    except Exception as e:
        logger.error("Error generando métricas", error=str(e))
        return PlainTextResponse(
            content=f"# Error generating metrics: {str(e)}",
            status_code=500
        )


async def update_job_metrics():
    """Actualiza métricas de jobs"""
    try:
        # Obtener estadísticas de jobs por tipo y estado
        from app.models.domain import JobType, JobStatus
        
        for job_type in JobType:
            for status in JobStatus:
                count = await mongo_repository._jobs_collection.count_documents({
                    "type": job_type.value,
                    "status": status.value
                })
                active_jobs.labels(type=job_type.value, status=status.value).set(count)
                
    except Exception as e:
        logger.error("Error actualizando métricas de jobs", error=str(e))


async def update_storage_metrics():
    """Actualiza métricas de almacenamiento"""
    try:
        storage = LocalStorageService()
        stats = await storage.get_storage_stats()
        
        if "used_space_gb" in stats:
            # Convertir GB a bytes
            used_bytes = stats["used_space_gb"] * (1024**3)
            storage_usage.set(used_bytes)
            
    except Exception as e:
        logger.error("Error actualizando métricas de almacenamiento", error=str(e))


# Middleware para actualizar métricas de requests
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Procesar request
        response = await call_next(request)
        
        # Actualizar métricas
        duration = time.time() - start_time
        
        # Aquí podrías añadir más métricas de requests
        
        return response
