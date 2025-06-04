"""
Endpoints para gestión de jobs
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import DESCENDING

from app.core import logger
from app.models.schemas import (
    JobResponse, JobListResponse, JobCancelRequest,
    SuccessResponse, PaginationParams
)
from app.models.domain import JobStatus
from app.services.database import MongoRepository
from app.api.v1.dependencies import (
    verify_api_key, get_db, get_pagination_params,
    validate_document_id
)


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filtrar por estado"),
    job_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    database: Optional[str] = Query(None, description="Filtrar por base de datos"),
    collection: Optional[str] = Query(None, description="Filtrar por colección"),
    pagination: PaginationParams = Depends(get_pagination_params),
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Lista jobs con filtros opcionales
    
    Args:
        status: Estado del job
        job_type: Tipo de job
        database: Base de datos
        collection: Colección
        pagination: Parámetros de paginación
        
    Returns:
        Lista paginada de jobs
    """
    try:
        # Obtener jobs
        jobs, total = await db.list_jobs(
            status=status,
            job_type=job_type,
            database=database,
            collection=collection,
            skip=pagination.skip,
            limit=pagination.limit,
            sort_by="created_at",
            sort_order=DESCENDING
        )
        
        # Calcular páginas
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        # Convertir a respuesta
        job_responses = [JobResponse(**job.to_dict()) for job in jobs]
        
        return JobListResponse(
            jobs=job_responses,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error("Error listando jobs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Obtiene un job por ID
    
    Args:
        job_id: ID del job
        
    Returns:
        Job encontrado
    """
    try:
        # Validar ID
        job_id = validate_document_id(job_id)
        
        # Obtener job
        job = await db.get_job(job_id)
        
        return JobResponse(**job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}", response_model=SuccessResponse)
async def cancel_job(
    job_id: str,
    request: Optional[JobCancelRequest] = None,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Cancela un job en ejecución
    
    Args:
        job_id: ID del job
        request: Datos de cancelación
        
    Returns:
        Confirmación de cancelación
    """
    try:
        # Validar ID
        job_id = validate_document_id(job_id)
        
        # Obtener job
        job = await db.get_job(job_id)
        
        # Verificar que se puede cancelar
        if job.is_finished:
            raise HTTPException(
                status_code=400,
                detail=f"El job ya está en estado {job.status.value}"
            )
        
        # Cancelar job
        job.cancel()
        if request and request.reason:
            job.add_error(f"Cancelado: {request.reason}", "UserCancellation")
        
        # Actualizar en base de datos
        await db.update_job(job)
        
        logger.info("Job cancelado", job_id=job_id, reason=request.reason if request else None)
        
        return SuccessResponse(
            message=f"Job {job_id} cancelado exitosamente",
            data={"job_id": job_id, "status": job.status.value}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cancelando job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/errors", response_model=List[dict])
async def get_job_errors(
    job_id: str,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Obtiene los errores de un job
    
    Args:
        job_id: ID del job
        
    Returns:
        Lista de errores del job
    """
    try:
        # Validar ID
        job_id = validate_document_id(job_id)
        
        # Obtener job
        job = await db.get_job(job_id)
        
        # Convertir errores a diccionarios
        errors = []
        for error in job.errors:
            errors.append({
                "timestamp": error.timestamp.isoformat(),
                "message": error.message,
                "error_type": error.error_type,
                "details": error.details
            })
        
        return errors
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error obteniendo errores del job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Reintenta un job fallido
    
    Args:
        job_id: ID del job
        
    Returns:
        Nuevo job creado
    """
    try:
        # Validar ID
        job_id = validate_document_id(job_id)
        
        # Obtener job original
        original_job = await db.get_job(job_id)
        
        # Verificar que el job falló
        if original_job.status != JobStatus.FAILED:
            raise HTTPException(
                status_code=400,
                detail=f"Solo se pueden reintentar jobs fallidos. Estado actual: {original_job.status.value}"
            )
        
        # Crear nuevo job basado en el original
        from uuid import uuid4
        new_job = Job(
            id=str(uuid4()),
            type=original_job.type,
            status=JobStatus.PENDING,
            database=original_job.database,
            collection=original_job.collection,
            document_id=original_job.document_id,
            filter_query=original_job.filter_query,
            metadata={
                **original_job.metadata,
                "retry_of": original_job.id,
                "retry_count": original_job.metadata.get("retry_count", 0) + 1
            }
        )
        
        # Guardar nuevo job
        new_job = await db.create_job(new_job)
        
        # Encolar para procesamiento
        from app.workers.tasks import process_download_job
        process_download_job.delay(new_job.id)
        
        logger.info(
            "Job reintentado",
            original_job_id=job_id,
            new_job_id=new_job.id
        )
        
        return JobResponse(**new_job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error reintentando job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
