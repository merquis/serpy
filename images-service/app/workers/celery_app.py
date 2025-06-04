"""
Configuración de Celery para procesamiento asíncrono
"""
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
import asyncio
from typing import Any

from app.core import settings, logger, setup_logging
from app.services.database import mongo_repository


# Crear instancia de Celery
celery_app = Celery(
    "images-service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"]
)

# Configuración de Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora máximo por tarea
    task_soft_time_limit=3300,  # Warning a los 55 minutos
    worker_prefetch_multiplier=1,  # Para tareas largas, mejor 1
    worker_max_tasks_per_child=50,  # Reiniciar worker después de 50 tareas
    task_acks_late=True,  # Acknowledge después de completar
    worker_send_task_events=True,
    task_send_sent_event=True,
    result_expires=86400,  # Resultados expiran en 24 horas
)

# Configuración de rutas de tareas
celery_app.conf.task_routes = {
    "app.workers.tasks.download.*": {"queue": "downloads"},
    "app.workers.tasks.process.*": {"queue": "processing"},
}

# Configuración de colas
celery_app.conf.task_queues = {
    "downloads": {
        "exchange": "downloads",
        "exchange_type": "direct",
        "routing_key": "download",
    },
    "processing": {
        "exchange": "processing",
        "exchange_type": "direct",
        "routing_key": "process",
    },
}


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Se ejecuta cuando el worker está listo"""
    setup_logging(log_level="INFO" if settings.is_production else "DEBUG")
    logger.info("Worker de Celery iniciado", environment=settings.environment)
    
    # Conectar a MongoDB en el contexto del worker
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(mongo_repository.connect())
    logger.info("Conexión a MongoDB establecida en worker")


@worker_shutdown.connect
def on_worker_shutdown(**kwargs):
    """Se ejecuta cuando el worker se cierra"""
    logger.info("Worker de Celery cerrándose")
    
    # Desconectar de MongoDB
    loop = asyncio.get_event_loop()
    loop.run_until_complete(mongo_repository.disconnect())
    logger.info("Conexión a MongoDB cerrada en worker")


class AsyncTask:
    """Decorador para tareas asíncronas en Celery"""
    
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(func(*args, **kwargs))
            finally:
                loop.close()
        
        # Registrar la tarea en Celery
        return celery_app.task(*self.args, **self.kwargs)(wrapper)


# Función helper para ejecutar código asíncrono
def run_async(coro):
    """Ejecuta una corrutina en el contexto de Celery"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
