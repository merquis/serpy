"""
Endpoint para servir imágenes descargadas
"""
from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path as PathLib
import os

from app.core import settings, logger

router = APIRouter(prefix="/images", tags=["serve"])


# IMPORTANTE: El orden importa - primero la ruta más específica (con /)
@router.get("/{database}/{collection}/{document_id}/", name="list_document_images_with_slash")
@router.get("/{database}/{collection}/{document_id}", name="list_document_images")
async def list_document_images(
    database: str = Path(..., description="Nombre de la base de datos"),
    collection: str = Path(..., description="Nombre de la colección"),
    document_id: str = Path(..., description="ID del documento")
):
    """
    Lista todas las imágenes disponibles para un documento específico (ej: un hotel).
    
    URL ejemplo:
    https://images.serpsrewrite.com/api/v1/images/serpy_db/hotel-booking/6840bc4e949575a0325d921b-vincci-seleccin-la-plantacin-del-sur/
    """
    doc_path = settings.storage_path / database / collection / document_id
    
    if not doc_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron imágenes para el documento {document_id}"
        )
    
    images = []
    
    # Función recursiva para buscar imágenes
    def find_images(path, base_path=""):
        for item in path.iterdir():
            if item.is_file() and item.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                relative_path = f"{base_path}/{item.name}" if base_path else item.name
                full_url = f"https://images.serpsrewrite.com/api/v1/images/{database}/{collection}/{document_id}/{relative_path}"
                size_bytes = item.stat().st_size
                size_kb = round(size_bytes / 1024, 2)
                images.append({
                    "filename": relative_path,
                    "size": f"{size_kb} KB",
                    "url": full_url
                })
            elif item.is_dir():
                subdir_name = item.name
                find_images(item, f"{base_path}/{subdir_name}" if base_path else subdir_name)
    
    # Buscar todas las imágenes
    find_images(doc_path)
    
    # Ordenar por nombre de archivo
    images.sort(key=lambda x: x['filename'])
    
    return {
        "database": database,
        "collection": collection,
        "document_id": document_id,
        "total_images": len(images),
        "images": images,
        "base_url": f"https://images.serpsrewrite.com/api/v1/images/{database}/{collection}/{document_id}/"
    }


@router.get("/{database}/{collection}/{document_id}/{filename:path}")
async def serve_image(
    database: str = Path(..., description="Nombre de la base de datos"),
    collection: str = Path(..., description="Nombre de la colección"),
    document_id: str = Path(..., description="ID del documento"),
    filename: str = Path(..., description="Nombre del archivo de imagen (puede incluir subdirectorios)")
):
    """
    Sirve una imagen descargada por su ruta.
    
    La URL sería algo como:
    https://images.serpsrewrite.com/api/v1/images/serpy_db/hotel-booking/6840bc4e949575a0325d921b/original/img_001.jpg
    """
    # Construir la ruta completa
    image_path = settings.storage_path / database / collection / document_id / filename
    
    # Verificar que el archivo existe
    if not image_path.exists():
        logger.warning(
            "Imagen no encontrada",
            path=str(image_path),
            database=database,
            collection=collection,
            document_id=document_id,
            filename=filename
        )
        raise HTTPException(
            status_code=404,
            detail=f"Imagen no encontrada: {filename}"
        )
    
    # Verificar que es un archivo (no un directorio)
    if not image_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="La ruta no corresponde a un archivo"
        )
    
    # Determinar el tipo MIME basado en la extensión
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon"
    }
    
    ext = image_path.suffix.lower()
    media_type = mime_types.get(ext, "application/octet-stream")
    
    logger.info(
        "Sirviendo imagen",
        path=str(image_path),
        size=image_path.stat().st_size,
        media_type=media_type
    )
    
    # Devolver la imagen
    return FileResponse(
        path=str(image_path),
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache por 1 día
            "X-Content-Type-Options": "nosniff"
        }
    )


@router.get("/{database}/{collection}")
async def list_collection_images(
    database: str = Path(..., description="Nombre de la base de datos"),
    collection: str = Path(..., description="Nombre de la colección")
):
    """
    Lista todas las imágenes disponibles para una colección.
    
    Devuelve una estructura con los documentos y sus imágenes.
    """
    collection_path = settings.storage_path / database / collection
    
    if not collection_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron imágenes para {database}/{collection}"
        )
    
    result = {
        "database": database,
        "collection": collection,
        "documents": {}
    }
    
    # Recorrer los directorios de documentos
    for doc_dir in collection_path.iterdir():
        if doc_dir.is_dir():
            doc_id = doc_dir.name
            images = []
            
            # Función recursiva para buscar imágenes en subdirectorios
            def find_images(path, base_path=""):
                for item in path.iterdir():
                    if item.is_file() and item.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        relative_path = f"{base_path}/{item.name}" if base_path else item.name
                        images.append({
                            "filename": relative_path,
                            "size": item.stat().st_size,
                            "url": f"/api/v1/images/{database}/{collection}/{doc_id}/{relative_path}"
                        })
                    elif item.is_dir():
                        # Buscar en subdirectorios (como 'original')
                        subdir_name = item.name
                        find_images(item, f"{base_path}/{subdir_name}" if base_path else subdir_name)
            
            # Buscar imágenes recursivamente
            find_images(doc_dir)
            
            if images:
                result["documents"][doc_id] = {
                    "total_images": len(images),
                    "images": images
                }
    
    result["total_documents"] = len(result["documents"])
    
    return result


@router.get("/")
async def list_all_images():
    """
    Lista todas las bases de datos y colecciones con imágenes disponibles.
    """
    result = {
        "databases": {}
    }
    
    # Verificar que el directorio de almacenamiento existe
    if not settings.storage_path.exists():
        return result
    
    # Recorrer bases de datos
    for db_dir in settings.storage_path.iterdir():
        if db_dir.is_dir():
            db_name = db_dir.name
            collections = []
            
            # Recorrer colecciones
            for coll_dir in db_dir.iterdir():
                if coll_dir.is_dir():
                    # Contar documentos
                    doc_count = sum(1 for d in coll_dir.iterdir() if d.is_dir())
                    if doc_count > 0:
                        collections.append({
                            "name": coll_dir.name,
                            "documents": doc_count,
                            "url": f"/api/v1/images/{db_name}/{coll_dir.name}"
                        })
            
            if collections:
                result["databases"][db_name] = {
                    "collections": collections,
                    "total_collections": len(collections)
                }
    
    result["total_databases"] = len(result["databases"])
    
    return result
