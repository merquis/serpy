"""
Tareas de Celery para descarga de imágenes
"""
from typing import Dict, Any, Optional
import httpx

from app.workers.celery_app import celery_app, AsyncTask, run_async
from app.core import logger
from app.models.domain import Job, JobType, JobStatus
from app.services.database import mongo_repository
from app.services.download import DownloadService
from app.services.storage import LocalStorageService
from app.models.schemas import WebhookPayload


@celery_app.task(name="app.workers.tasks.download.process_download_job")
def process_download_job(job_id: str) -> Dict[str, Any]:
    """
    Procesa un job de descarga de imágenes
    
    Args:
        job_id: ID del job a procesar
        
    Returns:
        Diccionario con el resultado del procesamiento
    """
    logger.info("Iniciando tarea de descarga", job_id=job_id)
    
    async def _process():
        try:
            # Obtener job
            job = await mongo_repository.get_job(job_id)
            
            if job.status != JobStatus.PENDING:
                logger.warning("Job no está en estado PENDING", job_id=job_id, status=job.status.value)
                return {
                    "success": False,
                    "error": f"Job en estado {job.status.value}, se esperaba PENDING"
                }
            
            # Crear servicio de descarga
            storage = LocalStorageService()
            download_service = DownloadService(storage)
            
            # Procesar job
            await download_service.process_job(job)
            
            # Enviar webhook si está configurado
            await send_webhook_notification(job, "completed")
            
            return {
                "success": True,
                "job_id": job_id,
                "processed_items": job.processed_items,
                "failed_items": job.failed_items,
                "duration": job.duration
            }
            
        except Exception as e:
            logger.error("Error procesando job de descarga", job_id=job_id, error=str(e))
            
            # Intentar marcar el job como fallido
            try:
                job = await mongo_repository.get_job(job_id)
                job.fail(str(e))
                await mongo_repository.update_job(job)
                await send_webhook_notification(job, "failed")
            except:
                pass
            
            return {
                "success": False,
                "error": str(e)
            }
    
    return run_async(_process())


@celery_app.task(name="app.workers.tasks.download.check_and_process_pending_jobs")
def check_and_process_pending_jobs() -> Dict[str, Any]:
    """
    Verifica y procesa jobs pendientes
    Esta tarea puede ser ejecutada periódicamente
    """
    logger.info("Verificando jobs pendientes")
    
    async def _check():
        try:
            # Obtener jobs pendientes
            pending_jobs = await mongo_repository.get_pending_jobs(limit=5)
            
            if not pending_jobs:
                logger.info("No hay jobs pendientes")
                return {
                    "success": True,
                    "pending_jobs": 0,
                    "queued_jobs": []
                }
            
            # Encolar jobs para procesamiento
            queued = []
            for job in pending_jobs:
                try:
                    # Enviar a cola de Celery
                    process_download_job.delay(job.id)
                    queued.append(job.id)
                    logger.info("Job encolado para procesamiento", job_id=job.id)
                except Exception as e:
                    logger.error("Error encolando job", job_id=job.id, error=str(e))
            
            return {
                "success": True,
                "pending_jobs": len(pending_jobs),
                "queued_jobs": queued
            }
            
        except Exception as e:
            logger.error("Error verificando jobs pendientes", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    return run_async(_check())


async def send_webhook_notification(job: Job, event: str) -> None:
    """Envía notificación webhook si está configurado"""
    from app.core import settings
    
    if not settings.webhook_url:
        return
    
    try:
        # Preparar payload
        payload = WebhookPayload(
            event=f"job.{event}",
            job_id=job.id,
            status=job.status.value,
            data={
                "type": job.type.value,
                "database": job.database,
                "collection": job.collection,
                "total_items": job.total_items,
                "processed_items": job.processed_items,
                "failed_items": job.failed_items,
                "duration": job.duration,
                "errors": len(job.errors)
            }
        )
        
        # Enviar webhook
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                settings.webhook_url,
                json=payload.dict(),
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
        logger.info("Webhook enviado exitosamente", event=event, job_id=job.id)
        
    except Exception as e:
        logger.error("Error enviando webhook", event=event, job_id=job.id, error=str(e))


# Tareas periódicas (opcional)
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "check-pending-jobs": {
        "task": "app.workers.tasks.download.check_and_process_pending_jobs",
        "schedule": crontab(minute="*/5"),  # Cada 5 minutos
        "options": {"queue": "downloads"}
    },
}
