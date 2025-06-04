"""
Interfaz base para servicios de almacenamiento
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path
import aiofiles
import json

from app.core import logger
from app.models.domain import ImageMetadata


class StorageService(ABC):
    """Interfaz base para servicios de almacenamiento"""
    
    @abstractmethod
    async def save_file(self, file_path: Path, content: bytes) -> None:
        """Guarda un archivo en el almacenamiento"""
        pass
    
    @abstractmethod
    async def read_file(self, file_path: Path) -> bytes:
        """Lee un archivo del almacenamiento"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_path: Path) -> None:
        """Elimina un archivo del almacenamiento"""
        pass
    
    @abstractmethod
    async def exists(self, file_path: Path) -> bool:
        """Verifica si un archivo existe"""
        pass
    
    @abstractmethod
    async def list_files(self, directory: Path) -> list[Path]:
        """Lista archivos en un directorio"""
        pass
    
    @abstractmethod
    async def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Obtiene información de un archivo"""
        pass
    
    async def save_metadata(self, metadata: ImageMetadata, base_path: Path) -> None:
        """Guarda metadata en formato JSON"""
        metadata_path = base_path / "metadata.json"
        content = json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False)
        await self.save_file(metadata_path, content.encode('utf-8'))
        logger.info("Metadata guardada", path=str(metadata_path))
    
    async def read_metadata(self, base_path: Path) -> Optional[ImageMetadata]:
        """Lee metadata desde JSON"""
        metadata_path = base_path / "metadata.json"
        
        if not await self.exists(metadata_path):
            return None
        
        try:
            content = await self.read_file(metadata_path)
            data = json.loads(content.decode('utf-8'))
            return ImageMetadata.from_dict(data)
        except Exception as e:
            logger.error("Error leyendo metadata", path=str(metadata_path), error=str(e))
            return None
