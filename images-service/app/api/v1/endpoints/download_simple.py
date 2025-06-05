"""
Endpoint simplificado para descargar imágenes sin MongoDB
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from uuid import uuid4
import httpx
import asyncio
from pathlib import Path
import json
from datetime import datetime

from app.core import logger, settings
from app.api.v1.dependencies import verify_api_key

router = APIRouter(prefix="/download", tags=["download"])


async def download_image(session, url, save_path):
    """Descarga una imagen"""
    try:
        response = await session.get(url, timeout=30.0)
        response.raise_for_status()
        
        # Guardar imagen
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        
        logger.info(f"Imagen descargada: {save_path.name}")
        return True
    except Exception as e:
        logger.error(f"Error descargando {url}: {e}")
        return False


class DownloadRequest(BaseModel):
    api_url: str
    database_name: Optional[str] = None
    collection_name: Optional[str] = None

@router.post("/from-api-url-simple")
async def download_from_api_url_simple(
    request: DownloadRequest,
    background_tasks: BackgroundTasks = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Descarga imágenes desde una URL de API externa (sin MongoDB)
    
    Args:
        api_url: URL de la API que contiene los documentos con imágenes
        database_name: Nombre opcional para la base de datos (por defecto 'serpy_db')
        collection_name: Nombre opcional para la colección
        
    Returns:
        Resultado de la descarga
    """
    try:
        # Extraer valores del request
        api_url = request.api_url
        database_name = request.database_name
        collection_name = request.collection_name
        
        # Usar base de datos por defecto si no se proporciona
        if not database_name:
            database_name = "serpy_db"
            
        # Extraer nombre de colección de la URL si no se proporciona
        if not collection_name:
            collection_name = api_url.rstrip('/').split('/')[-1]
            if not collection_name or collection_name == "api":
                collection_name = "external-api-data"
        
        logger.info(
            "Iniciando descarga directa desde API externa",
            api_url=api_url,
            database_name=database_name,
            collection_name=collection_name
        )
        
        # Obtener datos de la API externa
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            response.raise_for_status()
            data = response.json()
        
        # Extraer documentos
        documents = []
        if isinstance(data, list):
            documents = data
        elif isinstance(data, dict):
            documents = data.get('documents', data.get('data', []))
            if not documents and 'documents' not in data and 'data' not in data:
                documents = [data]
        
        if not documents:
            raise HTTPException(
                status_code=400,
                detail="No se encontraron documentos en la respuesta de la API"
            )
        
        # Procesar documentos y descargar imágenes
        total_images = 0
        downloaded = 0
        job_id = str(uuid4())
        
        async with httpx.AsyncClient() as session:
            for doc in documents:
                # Extraer ID y nombre
                doc_id = doc.get('_id', doc.get('id', str(uuid4())))
                nombre = doc.get('nombre_alojamiento', doc.get('titulo_h1', 'sin-nombre'))
                
                # Sanitizar nombre
                nombre_safe = settings.sanitize_filename(nombre)
                
                # Crear directorio
                doc_dir = settings.storage_path / database_name / collection_name / f"{doc_id}-{nombre_safe}" / "original"
                doc_dir.mkdir(parents=True, exist_ok=True)
                
                # Buscar imágenes
                imagenes = doc.get('imagenes', [])
                if not imagenes:
                    for field in ['images', 'fotos', 'photos', 'galeria']:
                        if field in doc and isinstance(doc[field], list):
                            imagenes = doc[field]
                            break
                
                if not imagenes:
                    logger.warning(f"No se encontraron imágenes en documento {doc_id}")
                    continue
                
                total_images += len(imagenes)
                
                # Descargar imágenes
                tasks = []
                for i, img_url in enumerate(imagenes):
                    if isinstance(img_url, str) and img_url.startswith('http'):
                        ext = '.jpg'
                        if '.png' in img_url.lower():
                            ext = '.png'
                        elif '.webp' in img_url.lower():
                            ext = '.webp'
                        
                        save_path = doc_dir / f"img_{i+1:03d}{ext}"
                        tasks.append(download_image(session, img_url, save_path))
                
                if tasks:
                    results = await asyncio.gather(*tasks)
                    downloaded += sum(results)
                
                # Guardar metadata
                metadata = {
                    "document_id": str(doc_id),
                    "nombre": nombre,
                    "total_images": len(imagenes),
                    "downloaded": sum(results) if tasks else 0,
                    "timestamp": datetime.now().isoformat(),
                    "source_url": api_url,
                    "job_id": job_id
                }
                
                metadata_path = doc_dir.parent / "metadata.json"
                metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        logger.info(
            "Descarga completada",
            job_id=job_id,
            total_images=total_images,
            downloaded=downloaded
        )
        
        return {
            "id": job_id,
            "status": "completed",
            "api_url": api_url,
            "database": database_name,
            "collection": collection_name,
            "documents_processed": len(documents),
            "total_images": total_images,
            "images_downloaded": downloaded,
            "storage_path": str(settings.storage_path / database_name / collection_name)
        }
        
    except httpx.HTTPError as e:
        logger.error("Error obteniendo datos de la API", api_url=api_url, error=str(e))
        raise HTTPException(status_code=400, detail=f"Error accediendo a la API: {str(e)}")
    except Exception as e:
        logger.error("Error en descarga directa", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
