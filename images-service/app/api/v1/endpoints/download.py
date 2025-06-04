"""
Endpoints para gestión de descargas
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from uuid import uuid4
import httpx

from app.core import logger
from app.models.schemas import (
    JobCreateRequest, JobResponse, BatchDownloadRequest,
    SuccessResponse, ErrorResponse
)
from app.models.domain import Job, JobType, JobStatus
from app.services.database.mongo_repository import MongoRepository
from app.workers.tasks import process_download_job
from app.api.v1.dependencies import (
    verify_api_key, get_db, validate_database_name,
    validate_collection_name, validate_document_id
)


router = APIRouter(prefix="/download", tags=["download"])


@router.post("/from-api-url", response_model=JobResponse)
async def download_from_api_url(
    api_url: str,
    collection_name: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    api_key: str = Depends(verify_api_key),
    db: MongoRepository = Depends(get_db)
):
    """
    Descarga imágenes desde una URL de API externa
    
    Args:
        api_url: URL de la API que contiene los documentos con imágenes
        collection_name: Nombre opcional para la colección (se extrae de la URL si no se proporciona)
        
    Returns:
        Job creado
    """
    try:
        # Extraer nombre de colección de la URL si no se proporciona
        if not collection_name:
            # Extraer el último segmento de la URL como nombre de colección
            collection_name = api_url.rstrip('/').split('/')[-1]
            if not collection_name or collection_name == "api":
                collection_name = "external-api-data"
        
        logger.info(
            "Iniciando descarga desde API externa",
            api_url=api_url,
            collection_name=collection_name
        )
        
        # Obtener datos de la API externa
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
        
        # Extraer documentos (puede venir como 'documents', 'data', o directamente como array)
        documents = []
        if isinstance(data, list):
            documents = data
        elif isinstance(data, dict):
            documents = data.get('documents', data.get('data', []))
            if not documents and 'documents' not in data and 'data' not in data:
                # Si no hay campo documents o data, asumir que es un solo documento
                documents = [data]
        
        if not documents:
            raise HTTPException(
                status_code=400,
                detail="No se encontraron documentos en la respuesta de la API"
            )
        
        # Guardar documentos temporalmente en MongoDB
        temp_collection = f"temp_{collection_name}_{uuid4().hex[:8]}"
        
        # Insertar documentos en colección temporal
        for doc in documents:
            await db._ensure_connected()
            col = await db.get_collection("serpy_db", temp_collection)
            await col.insert_one(doc)
        
        # Crear job para procesar la colección temporal
        job = Job(
            id=str(uuid4()),
            type=JobType.DOWNLOAD_COLLECTION,
            status=JobStatus.PENDING,
            database="serpy_db",
            collection=temp_collection,
            metadata={
                "source": "external_api",
                "api_url": api_url,
                "original_collection": collection_name,
                "total_documents": len(documents),
                "cleanup_collection": True  # Marcar para limpiar después
            }
        )
        
        # Guardar en base de datos
        job = await db.create_job(job)
        
        # Encolar para procesamiento
        process_download_job.delay(job.id)
        
        logger.info(
            "Job de descarga desde API creado",
            job_id=job.id,
            api_url=api_url,
            documents=len(documents)
        )
        
        return JobResponse(**job.to_dict())
        
    except httpx.HTTPError as e:
        logger.error("Error obteniendo datos de la API", api_url=api_url, error=str(e))
        raise HTTPException(status_code=400, detail=f"Error accediendo a la API: {str(e)}")
    except Exception as e:
        logger.error("Error creando job de descarga desde API", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
