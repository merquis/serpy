"""
Servicio principal de descarga que orquesta el proceso completo
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from app.core import logger, settings
from app.core.exceptions import DownloadException, StorageException
from app.models.domain import Job, JobStatus, ImageMetadata, ImageInfo
from app.services.database.mongo_repository import mongo_repository
from app.services.storage.local_storage import LocalStorageService
from app.services.storage.base import StorageService
from .image_downloader import ImageDownloader


class DownloadService:
    """Servicio principal que orquesta la descarga de imágenes"""
    
    def __init__(self, storage_service: Optional[StorageService] = None):
        self.storage = storage_service or LocalStorageService()
        self.db = mongo_repository
    
    async def process_job(self, job: Job) -> None:
        """Procesa un job de descarga"""
        try:
            logger.info("Iniciando procesamiento de job", job_id=job.id, type=job.type.value)
            
            # Marcar job como iniciado
            job.start()
            await self.db.update_job(job)
            
            # Procesar según el tipo de job
            if job.type.value == "download_collection":
                await self._process_collection(job)
            elif job.type.value == "download_document":
                await self._process_document(job)
            elif job.type.value == "download_batch":
                await self._process_batch(job)
            else:
                raise ValueError(f"Tipo de job no soportado: {job.type}")
            
            # Marcar job como completado
            job.complete()
            await self.db.update_job(job)
            
            # Limpiar colección temporal si es necesario
            if job.metadata.get("cleanup_collection"):
                try:
                    await self._cleanup_temp_collection(job)
                except Exception as e:
                    logger.warning("Error limpiando colección temporal", error=str(e))
            
            logger.info(
                "Job completado exitosamente",
                job_id=job.id,
                processed=job.processed_items,
                failed=job.failed_items,
                duration=job.duration
            )
            
        except Exception as e:
            logger.error("Error procesando job", job_id=job.id, error=str(e))
            job.fail(str(e))
            await self.db.update_job(job)
            raise
    
    async def _process_collection(self, job: Job) -> None:
        """Procesa descarga de una colección completa"""
        # Contar documentos
        total_docs = await self.db.count_documents(job.database, job.collection)
        job.total_items = total_docs
        await self.db.update_job(job)
        
        logger.info(
            "Procesando colección",
            database=job.database,
            collection=job.collection,
            total_documents=total_docs
        )
        
        # Procesar documentos en lotes
        batch_size = 10
        processed = 0
        
        async for doc in self.db.find_documents(job.database, job.collection):
            await self._process_document_images(job, doc)
            
            processed += 1
            job.processed_items = processed
            
            # Actualizar progreso cada X documentos
            if processed % batch_size == 0:
                await self.db.update_job(job)
                logger.info(
                    "Progreso de descarga",
                    job_id=job.id,
                    processed=processed,
                    total=total_docs,
                    percentage=job.progress_percentage
                )
    
    async def _process_document(self, job: Job) -> None:
        """Procesa descarga de un documento específico"""
        if not job.document_id:
            raise ValueError("document_id es requerido para download_document")
        
        # Obtener documento
        doc = await self.db.get_document(job.database, job.collection, job.document_id)
        
        job.total_items = 1
        await self.db.update_job(job)
        
        # Procesar imágenes del documento
        await self._process_document_images(job, doc)
        
        job.processed_items = 1
        await self.db.update_job(job)
    
    async def _process_batch(self, job: Job) -> None:
        """Procesa descarga batch con filtros custom"""
        filter_query = job.filter_query or {}
        limit = job.metadata.get("limit")
        skip = job.metadata.get("skip", 0)

        # Contar documentos que coinciden con el filtro
        total_docs = await self.db.count_documents(job.database, job.collection, filter_query)

        # Calcular cantidad efectiva aplicando skip y limit
        effective_total = max(total_docs - (skip or 0), 0)
        if limit and limit < effective_total:
            effective_total = limit

        job.total_items = effective_total
        await self.db.update_job(job)

        logger.info(
            "Procesando batch",
            database=job.database,
            collection=job.collection,
            filter=filter_query,
            total_documents=effective_total,
            skip=skip,
            limit=limit,
        )

        # Procesar documentos
        processed = 0
        async for doc in self.db.find_documents(
            job.database,
            job.collection,
            filter_query=filter_query,
            skip=skip or 0,
            limit=limit or 0,
        ):
            await self._process_document_images(job, doc)

            processed += 1
            job.processed_items = processed
            
            if processed % 10 == 0:
                await self.db.update_job(job)
    
    async def _process_document_images(self, job: Job, document: Dict[str, Any]) -> None:
        """Procesa las imágenes de un documento"""
        try:
            # Extraer URLs de imágenes
            image_urls = await self.db.find_image_fields(document)
            
            if not image_urls:
                logger.warning(
                    "No se encontraron imágenes en el documento",
                    document_id=document.get("_id"),
                    collection=job.collection
                )
                return
            
            # Obtener campo de búsqueda para el nombre
            search_field = self._get_search_field(document)
            
            # Crear metadata
            metadata = ImageMetadata(
                document_id=str(document["_id"]),
                collection=job.collection,
                database=job.database,
                search_field=search_field,
                search_field_sanitized=settings.sanitize_filename(search_field),
                job_id=job.id
            )
            
            # Generar ruta de almacenamiento
            storage_path = settings.get_storage_path(
                job.database,
                job.collection,
                str(document["_id"]),
                search_field
            )
            
            # Crear directorio
            await self.storage.create_directory(storage_path / "original")
            
            # Descargar imágenes
            async with ImageDownloader() as downloader:
                # Callback de progreso
                async def progress_callback(current, total, url):
                    logger.debug(
                        "Progreso de descarga de documento",
                        document_id=document["_id"],
                        current=current,
                        total=total,
                        url=url
                    )
                
                # Descargar batch
                results = await downloader.download_batch(image_urls, progress_callback)
                
                # Procesar resultados
                for i, (content, image_info) in enumerate(results):
                    if content:
                        # Guardar imagen
                        image_path = storage_path / "original" / image_info.filename
                        await self.storage.save_file(image_path, content)
                        
                        logger.info(
                            "Imagen guardada",
                            path=str(image_path),
                            size_mb=image_info.size_mb,
                            dimensions=f"{image_info.width}x{image_info.height}"
                        )
                    
                    # Añadir a metadata (incluso si falló)
                    metadata.add_original_image(image_info)
                
                # Obtener estadísticas
                stats = downloader.get_stats()
                logger.info(
                    "Descarga de documento completada",
                    document_id=document["_id"],
                    total_images=stats["total_downloads"],
                    successful=stats["successful_downloads"],
                    failed=stats["failed_downloads"],
                    total_size_mb=stats["total_size_mb"]
                )
            
            # Guardar metadata
            await self.storage.save_metadata(metadata, storage_path)
            
            # Actualizar documento en MongoDB con rutas locales
            update_data = {
                "local_images_path": str(storage_path),
                "images_metadata": {
                    "total": metadata.total_images,
                    "successful": metadata.successful_downloads,
                    "failed": metadata.failed_downloads,
                    "size_mb": metadata.total_size_mb,
                    "processed_at": datetime.utcnow()
                }
            }
            
            await self.db.update_document(
                job.database,
                job.collection,
                str(document["_id"]),
                update_data
            )
            
        except Exception as e:
            logger.error(
                "Error procesando imágenes del documento",
                document_id=document.get("_id"),
                error=str(e)
            )
            job.add_error(
                f"Error en documento {document.get('_id')}: {str(e)}",
                "DocumentProcessingError",
                {"document_id": str(document.get("_id"))}
            )
            await self.db.update_job(job)
    
    def _get_search_field(self, document: Dict[str, Any]) -> str:
        """Obtiene el campo de búsqueda del documento"""
        # Prioridad de campos para usar como nombre
        search_fields = [
            "nombre_alojamiento",  # Para hoteles de booking
            "name", "title", "nombre", "titulo",
            "hotel_name", "property_name", "business_name",
            "display_name", "full_name"
        ]
        
        for field in search_fields:
            if field in document and document[field]:
                return str(document[field])
        
        # Si no hay campo de búsqueda, usar ID
        return f"document-{document.get('_id', 'unknown')}"
    
    async def get_document_images_info(
        self,
        database: str,
        collection: str,
        document_id: str
    ) -> Optional[ImageMetadata]:
        """Obtiene información de imágenes descargadas de un documento"""
        try:
            # Obtener documento para el campo de búsqueda
            doc = await self.db.get_document(database, collection, document_id)
            search_field = self._get_search_field(doc)
            
            # Generar ruta
            storage_path = settings.get_storage_path(
                database,
                collection,
                document_id,
                search_field
            )
            
            # Leer metadata
            metadata = await self.storage.read_metadata(storage_path)
            return metadata
            
        except Exception as e:
            logger.error(
                "Error obteniendo info de imágenes",
                database=database,
                collection=collection,
                document_id=document_id,
                error=str(e)
            )
            return None
    
    async def _cleanup_temp_collection(self, job: Job) -> None:
        """Limpia la colección temporal después de procesar"""
        try:
            logger.info(
                "Limpiando colección temporal",
                collection=job.collection,
                database=job.database
            )
            
            # Obtener la colección
            col = await self.db.get_collection(job.database, job.collection)
            
            # Eliminar la colección
            await col.drop()
            
            logger.info(
                "Colección temporal eliminada",
                collection=job.collection
            )
            
        except Exception as e:
            logger.error(
                "Error eliminando colección temporal",
                collection=job.collection,
                error=str(e)
            )
            raise
