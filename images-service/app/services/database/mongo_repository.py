"""
Repositorio MongoDB para el servicio de imágenes
"""
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId
import asyncio

from app.core import logger, settings
from app.core.exceptions import DatabaseException, NotFoundException
from app.models.domain import Job, JobStatus


class MongoRepository:
    """Repositorio para operaciones con MongoDB"""
    
    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._jobs_collection: Optional[AsyncIOMotorCollection] = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """Conecta a MongoDB"""
        async with self._lock:
            if self._client is not None:
                return
            
            try:
                logger.info("Conectando a MongoDB", uri=settings.mongodb_uri.split('@')[0] + "@...")
                
                self._client = AsyncIOMotorClient(
                    settings.mongodb_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=5000,
                    socketTimeoutMS=5000
                )
                
                # Verificar conexión
                await self._client.admin.command('ping')
                
                self._db = self._client[settings.mongodb_database]
                self._jobs_collection = self._db["image_jobs"]
                
                # Crear índices
                await self._create_indexes()
                
                logger.info("Conexión a MongoDB establecida", database=settings.mongodb_database)
                
            except Exception as e:
                logger.error("Error conectando a MongoDB", error=str(e))
                raise DatabaseException(f"No se pudo conectar a MongoDB: {str(e)}")
    
    async def disconnect(self) -> None:
        """Desconecta de MongoDB"""
        async with self._lock:
            if self._client:
                self._client.close()
                self._client = None
                self._db = None
                self._jobs_collection = None
                logger.info("Desconectado de MongoDB")
    
    async def _create_indexes(self) -> None:
        """Crea índices necesarios"""
        try:
            # Índices para jobs
            await self._jobs_collection.create_index([("status", ASCENDING)])
            await self._jobs_collection.create_index([("created_at", DESCENDING)])
            await self._jobs_collection.create_index([("type", ASCENDING), ("status", ASCENDING)])
            await self._jobs_collection.create_index([
                ("database", ASCENDING),
                ("collection", ASCENDING),
                ("status", ASCENDING)
            ])
            
            logger.info("Índices creados correctamente")
        except Exception as e:
            logger.warning("Error creando índices", error=str(e))
    
    async def _ensure_connected(self) -> None:
        """Asegura que hay conexión a MongoDB"""
        if self._client is None:
            await self.connect()
    
    # Operaciones con Jobs
    
    async def create_job(self, job: Job) -> Job:
        """Crea un nuevo job"""
        await self._ensure_connected()
        
        try:
            job_dict = job.to_dict()
            result = await self._jobs_collection.insert_one(job_dict)
            job.id = str(result.inserted_id)
            
            logger.info("Job creado", job_id=job.id, type=job.type.value)
            return job
            
        except Exception as e:
            logger.error("Error creando job", error=str(e))
            raise DatabaseException(f"Error creando job: {str(e)}")
    
    async def get_job(self, job_id: str) -> Job:
        """Obtiene un job por ID"""
        await self._ensure_connected()
        
        try:
            if not ObjectId.is_valid(job_id):
                raise NotFoundException("Job no encontrado", resource_type="job", resource_id=job_id)
            
            job_dict = await self._jobs_collection.find_one({"_id": ObjectId(job_id)})
            
            if not job_dict:
                raise NotFoundException("Job no encontrado", resource_type="job", resource_id=job_id)
            
            job_dict["_id"] = str(job_dict["_id"])
            return Job.from_dict(job_dict)
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("Error obteniendo job", job_id=job_id, error=str(e))
            raise DatabaseException(f"Error obteniendo job: {str(e)}")
    
    async def update_job(self, job: Job) -> Job:
        """Actualiza un job"""
        await self._ensure_connected()
        
        try:
            job_dict = job.to_dict()
            job_dict.pop("_id", None)  # Eliminar _id del update
            
            result = await self._jobs_collection.update_one(
                {"_id": ObjectId(job.id)},
                {"$set": job_dict}
            )
            
            if result.matched_count == 0:
                raise NotFoundException("Job no encontrado", resource_type="job", resource_id=job.id)
            
            logger.info("Job actualizado", job_id=job.id, status=job.status.value)
            return job
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("Error actualizando job", job_id=job.id, error=str(e))
            raise DatabaseException(f"Error actualizando job: {str(e)}")
    
    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        job_type: Optional[str] = None,
        database: Optional[str] = None,
        collection: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: int = DESCENDING
    ) -> tuple[List[Job], int]:
        """Lista jobs con filtros y paginación"""
        await self._ensure_connected()
        
        try:
            # Construir filtro
            filter_dict = {}
            if status:
                filter_dict["status"] = status.value
            if job_type:
                filter_dict["type"] = job_type
            if database:
                filter_dict["database"] = database
            if collection:
                filter_dict["collection"] = collection
            
            # Contar total
            total = await self._jobs_collection.count_documents(filter_dict)
            
            # Obtener jobs
            cursor = self._jobs_collection.find(filter_dict)
            cursor = cursor.sort(sort_by, sort_order)
            cursor = cursor.skip(skip).limit(limit)
            
            jobs = []
            async for job_dict in cursor:
                job_dict["_id"] = str(job_dict["_id"])
                jobs.append(Job.from_dict(job_dict))
            
            return jobs, total
            
        except Exception as e:
            logger.error("Error listando jobs", error=str(e))
            raise DatabaseException(f"Error listando jobs: {str(e)}")
    
    async def get_pending_jobs(self, limit: int = 10) -> List[Job]:
        """Obtiene jobs pendientes"""
        jobs, _ = await self.list_jobs(
            status=JobStatus.PENDING,
            limit=limit,
            sort_by="created_at",
            sort_order=ASCENDING
        )
        return jobs
    
    # Operaciones con documentos de MongoDB
    
    async def get_collection(self, database: str, collection: str) -> AsyncIOMotorCollection:
        """Obtiene una colección de MongoDB"""
        await self._ensure_connected()
        
        try:
            db = self._client[database]
            return db[collection]
        except Exception as e:
            logger.error("Error obteniendo colección", database=database, collection=collection, error=str(e))
            raise DatabaseException(f"Error obteniendo colección: {str(e)}")
    
    async def count_documents(self, database: str, collection: str, filter_query: Optional[Dict[str, Any]] = None) -> int:
        """Cuenta documentos en una colección"""
        try:
            col = await self.get_collection(database, collection)
            return await col.count_documents(filter_query or {})
        except Exception as e:
            logger.error("Error contando documentos", database=database, collection=collection, error=str(e))
            raise DatabaseException(f"Error contando documentos: {str(e)}")
    
    async def find_documents(
        self,
        database: str,
        collection: str,
        filter_query: Optional[Dict[str, Any]] = None,
        projection: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 0
    ) -> AsyncIterator[Dict[str, Any]]:
        """Busca documentos en una colección"""
        try:
            col = await self.get_collection(database, collection)
            cursor = col.find(filter_query or {}, projection=projection)
            
            if skip > 0:
                cursor = cursor.skip(skip)
            if limit > 0:
                cursor = cursor.limit(limit)
            
            async for doc in cursor:
                # Convertir ObjectId a string
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                yield doc
                
        except Exception as e:
            logger.error("Error buscando documentos", database=database, collection=collection, error=str(e))
            raise DatabaseException(f"Error buscando documentos: {str(e)}")
    
    async def get_document(self, database: str, collection: str, document_id: str) -> Dict[str, Any]:
        """Obtiene un documento por ID"""
        try:
            if not ObjectId.is_valid(document_id):
                raise NotFoundException("Documento no encontrado", resource_type="document", resource_id=document_id)
            
            col = await self.get_collection(database, collection)
            doc = await col.find_one({"_id": ObjectId(document_id)})
            
            if not doc:
                raise NotFoundException("Documento no encontrado", resource_type="document", resource_id=document_id)
            
            doc["_id"] = str(doc["_id"])
            return doc
            
        except NotFoundException:
            raise
        except Exception as e:
            logger.error("Error obteniendo documento", database=database, collection=collection, document_id=document_id, error=str(e))
            raise DatabaseException(f"Error obteniendo documento: {str(e)}")
    
    async def update_document(
        self,
        database: str,
        collection: str,
        document_id: str,
        update_data: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """Actualiza un documento"""
        try:
            if not ObjectId.is_valid(document_id):
                raise ValueError("ID de documento inválido")
            
            col = await self.get_collection(database, collection)
            
            # Añadir timestamp de actualización
            update_data["updated_at"] = datetime.utcnow()
            
            result = await col.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data},
                upsert=upsert
            )
            
            return result.modified_count > 0 or result.upserted_id is not None
            
        except Exception as e:
            logger.error("Error actualizando documento", database=database, collection=collection, document_id=document_id, error=str(e))
            raise DatabaseException(f"Error actualizando documento: {str(e)}")
    
    async def find_image_fields(self, document: Dict[str, Any]) -> List[str]:
        """Encuentra campos que contienen URLs de imágenes en un documento"""
        found_urls = []
        
        # Buscar específicamente el campo "images"
        if "images" in document and isinstance(document["images"], list):
            for image_obj in document["images"]:
                if isinstance(image_obj, dict) and "image_url" in image_obj:
                    url = image_obj["image_url"]
                    if isinstance(url, str) and url.startswith(("http://", "https://")):
                        found_urls.append(url)
        
        # También buscar en otros campos comunes por si acaso
        alternative_fields = ["images", "photos", "gallery", "media", "image_urls", "pictures", "imagen"]

        for field in alternative_fields:
            if field in document:
                if isinstance(document[field], list):
                    for url in document[field]:
                        if isinstance(url, str) and url.startswith(("http://", "https://")):
                            found_urls.append(url)
                elif isinstance(document[field], str) and document[field].startswith(("http://", "https://")):
                    found_urls.append(document[field])
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_urls = []
        for url in found_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls


# Instancia singleton del repositorio
mongo_repository = MongoRepository()
