"""
Servicio de descarga directa de imágenes sin depender del images-service externo
"""
import logging
import httpx
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DirectImageDownloadService:
    """Servicio para descargar imágenes directamente desde el scraper"""
    
    def __init__(self, base_path: str = "./downloaded_images"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    async def download_images_from_document(
        self, 
        mongo_id: str, 
        document_data: Dict[str, Any],
        collection_name: str,
        database_name: str = "serpy"
    ) -> Dict[str, Any]:
        """
        Descarga imágenes directamente desde los datos del documento
        
        Args:
            mongo_id: ID del documento en MongoDB
            document_data: Datos completos del documento con imágenes
            collection_name: Nombre de la colección
            database_name: Nombre de la base de datos
            
        Returns:
            Resultado de la descarga
        """
        try:
            # Extraer información del hotel
            hotel_name = document_data.get('nombre_alojamiento', 'hotel-sin-nombre')
            imagenes = document_data.get('imagenes', [])
            
            if not imagenes:
                return {
                    "success": False,
                    "error": "No se encontraron imágenes en el documento",
                    "mongo_id": mongo_id
                }
            
            # Sanitizar nombre del hotel
            hotel_name_safe = self._sanitize_filename(hotel_name)
            
            # Crear directorio de destino
            hotel_dir = self.base_path / database_name / collection_name / f"{mongo_id}-{hotel_name_safe}" / "original"
            hotel_dir.mkdir(parents=True, exist_ok=True)
            
            # Descargar imágenes
            downloaded = 0
            failed = 0
            download_results = []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i, img_url in enumerate(imagenes):
                    if not isinstance(img_url, str) or not img_url.startswith('http'):
                        continue
                    
                    try:
                        # Determinar extensión
                        ext = '.jpg'
                        if '.png' in img_url.lower():
                            ext = '.png'
                        elif '.webp' in img_url.lower():
                            ext = '.webp'
                        elif '.jpeg' in img_url.lower():
                            ext = '.jpeg'
                        
                        # Nombre del archivo
                        filename = f"img_{i+1:03d}{ext}"
                        file_path = hotel_dir / filename
                        
                        # Descargar imagen
                        logger.info(f"Descargando imagen {i+1}/{len(imagenes)}: {filename}")
                        response = await client.get(img_url)
                        response.raise_for_status()
                        
                        # Guardar imagen
                        file_path.write_bytes(response.content)
                        downloaded += 1
                        
                        download_results.append({
                            "filename": filename,
                            "url": img_url,
                            "size": len(response.content),
                            "status": "success"
                        })
                        
                        logger.info(f"✅ Imagen guardada: {filename} ({len(response.content)} bytes)")
                        
                    except Exception as e:
                        failed += 1
                        logger.error(f"❌ Error descargando imagen {i+1}: {str(e)}")
                        download_results.append({
                            "filename": f"img_{i+1:03d}",
                            "url": img_url,
                            "status": "failed",
                            "error": str(e)
                        })
            
            # Guardar metadata
            metadata = {
                "document_id": mongo_id,
                "hotel_name": hotel_name,
                "collection": collection_name,
                "database": database_name,
                "total_images": len(imagenes),
                "downloaded": downloaded,
                "failed": failed,
                "timestamp": datetime.now().isoformat(),
                "download_results": download_results
            }
            
            metadata_path = hotel_dir.parent / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
            
            return {
                "success": True,
                "mongo_id": mongo_id,
                "hotel_name": hotel_name,
                "total_images": len(imagenes),
                "downloaded": downloaded,
                "failed": failed,
                "storage_path": str(hotel_dir),
                "metadata_path": str(metadata_path),
                "download_results": download_results
            }
            
        except Exception as e:
            logger.error(f"Error en descarga directa: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "mongo_id": mongo_id
            }
    
    def _sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """Sanitiza un nombre de archivo"""
        # Convertir a minúsculas
        filename = filename.lower()
        
        # Reemplazar espacios y caracteres especiales por guiones
        import re
        filename = re.sub(r'[^a-z0-9\-]', '-', filename)
        
        # Eliminar guiones múltiples
        filename = re.sub(r'-+', '-', filename)
        
        # Eliminar guiones al inicio y final
        filename = filename.strip('-')
        
        # Limitar longitud
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        # Si queda vacío, usar un valor por defecto
        if not filename:
            filename = "hotel"
        
        return filename
