"""
Endpoints para gestión de descargas
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import uuid4

from app.core import logger
from app.models.schemas import (
    JobCreateRequest, JobResponse, BatchDownloadRequest,
    SuccessResponse, ErrorResponse
)
from app.models.domain import Job, JobType, JobStatus
from app.services.database import MongoRepository
from app.workers.tasks import process_download_job
from app.api.v1.dependencies import (
    verify_api_key, get_db, validate_database_name,
    validate_collection_name, validate_document_id
)


router = APIRouter(prefix="/download", tags=["download"])


@router.post("/collection/{database}/{collection}", response_model=JobResponse)
async def download_collection(
    database: str,
    collection: str,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Crea un job para descargar todas las imágenes de una colección
    
    Args:
        database: Nombre de la base de datos
        collection: Nombre de la colección
        
    Returns:
        Job creado
    """
    try:
        # Validar parámetros
        database = validate_database_name(database)
        collection = validate_collection_name(collection)
        
        # Verificar que la colección existe
        count = await db.count_documents(database, collection)
        if count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"La colección {collection} está vacía o no existe"
            )
        
        # Crear job
        job = Job(
            id=str(uuid4()),
            type=JobType.DOWNLOAD_COLLECTION,
            status=JobStatus.PENDING,
            database=database,
            collection=collection,
            metadata={"source": "api", "total_documents": count}
        )
        
        # Guardar en base de datos
        job = await db.create_job(job)
        
        # Encolar para procesamiento
        process_download_job.delay(job.id)
        
        logger.info(
            "Job de descarga de colección creado",
            job_id=job.id,
            database=database,
            collection=collection,
            documents=count
        )
        
        return JobResponse(**job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creando job de descarga", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/document/{database}/{collection}/{document_id}", response_model=JobResponse)
async def download_document(
    database: str,
    collection: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Crea un job para descargar las imágenes de un documento específico
    
    Args:
        database: Nombre de la base de datos
        collection: Nombre de la colección
        document_id: ID del documento
        
    Returns:
        Job creado
    """
    try:
        # Validar parámetros
        database = validate_database_name(database)
        collection = validate_collection_name(collection)
        document_id = validate_document_id(document_id)
        
        # Verificar que el documento existe
        doc = await db.get_document(database, collection, document_id)
        
        # Crear job
        job = Job(
            id=str(uuid4()),
            type=JobType.DOWNLOAD_DOCUMENT,
            status=JobStatus.PENDING,
            database=database,
            collection=collection,
            document_id=document_id,
            metadata={"source": "api"}
        )
        
        # Guardar en base de datos
        job = await db.create_job(job)
        
        # Encolar para procesamiento
        process_download_job.delay(job.id)
        
        logger.info(
            "Job de descarga de documento creado",
            job_id=job.id,
            database=database,
            collection=collection,
            document_id=document_id
        )
        
        return JobResponse(**job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creando job de descarga", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=JobResponse)
async def download_batch(
    request: BatchDownloadRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Crea un job para descargar imágenes con filtros custom
    
    Args:
        request: Parámetros de la descarga batch
        
    Returns:
        Job creado
    """
    try:
        # Validar parámetros
        database = validate_database_name(request.database)
        collection = validate_collection_name(request.collection)
        
        # Verificar que hay documentos que coinciden con el filtro
        count = await db.count_documents(database, collection, request.filter)
        if count == 0:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron documentos que coincidan con el filtro"
            )
        
        # Aplicar límites si están especificados
        if request.limit and request.limit < count:
            count = request.limit
        
        # Crear job
        job = Job(
            id=str(uuid4()),
            type=JobType.DOWNLOAD_BATCH,
            status=JobStatus.PENDING,
            database=database,
            collection=collection,
            filter_query=request.filter,
            metadata={
                "source": "api",
                "limit": request.limit,
                "skip": request.skip,
                "total_documents": count,
                **request.metadata
            }
        )
        
        # Guardar en base de datos
        job = await db.create_job(job)
        
        # Encolar para procesamiento
        process_download_job.delay(job.id)
        
        logger.info(
            "Job de descarga batch creado",
            job_id=job.id,
            database=database,
            collection=collection,
            filter=request.filter,
            documents=count
        )
        
        return JobResponse(**job.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creando job de descarga batch", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
