"""
Implementación de almacenamiento local
"""
from typing import Dict, Any, List
from pathlib import Path
import aiofiles
import aiofiles.os
import os
import shutil

from app.core import logger, settings
from app.core.exceptions import StorageException
from .base import StorageService


class LocalStorageService(StorageService):
    """Servicio de almacenamiento en sistema de archivos local"""
    
    def __init__(self, base_path: Path = None):
        self.base_path = base_path or settings.storage_path
        self._ensure_base_path()
    
    def _ensure_base_path(self):
        """Asegura que el directorio base existe"""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info("Directorio base de almacenamiento verificado", path=str(self.base_path))
        except Exception as e:
            raise StorageException(f"Error creando directorio base: {str(e)}", path=str(self.base_path))
    
    def _get_full_path(self, file_path: Path) -> Path:
        """Obtiene la ruta completa del archivo"""
        if file_path.is_absolute():
            return file_path
        return self.base_path / file_path
    
    async def save_file(self, file_path: Path, content: bytes) -> None:
        """Guarda un archivo en el sistema local"""
        full_path = self._get_full_path(file_path)
        
        try:
            # Crear directorio si no existe
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Guardar archivo
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content)
            
            logger.debug("Archivo guardado", path=str(full_path), size=len(content))
            
        except Exception as e:
            logger.error("Error guardando archivo", path=str(full_path), error=str(e))
            raise StorageException(f"Error guardando archivo: {str(e)}", path=str(full_path))
    
    async def read_file(self, file_path: Path) -> bytes:
        """Lee un archivo del sistema local"""
        full_path = self._get_full_path(file_path)
        
        try:
            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()
            
            logger.debug("Archivo leído", path=str(full_path), size=len(content))
            return content
            
        except FileNotFoundError:
            raise StorageException(f"Archivo no encontrado", path=str(full_path))
        except Exception as e:
            logger.error("Error leyendo archivo", path=str(full_path), error=str(e))
            raise StorageException(f"Error leyendo archivo: {str(e)}", path=str(full_path))
    
    async def delete_file(self, file_path: Path) -> None:
        """Elimina un archivo del sistema local"""
        full_path = self._get_full_path(file_path)
        
        try:
            if full_path.exists():
                await aiofiles.os.remove(full_path)
                logger.debug("Archivo eliminado", path=str(full_path))
            
        except Exception as e:
            logger.error("Error eliminando archivo", path=str(full_path), error=str(e))
            raise StorageException(f"Error eliminando archivo: {str(e)}", path=str(full_path))
    
    async def exists(self, file_path: Path) -> bool:
        """Verifica si un archivo existe"""
        full_path = self._get_full_path(file_path)
        return full_path.exists()
    
    async def list_files(self, directory: Path) -> List[Path]:
        """Lista archivos en un directorio"""
        full_path = self._get_full_path(directory)
        
        try:
            if not full_path.exists():
                return []
            
            files = []
            for item in full_path.iterdir():
                if item.is_file():
                    # Devolver ruta relativa al base_path
                    relative_path = item.relative_to(self.base_path)
                    files.append(relative_path)
            
            return files
            
        except Exception as e:
            logger.error("Error listando archivos", path=str(full_path), error=str(e))
            raise StorageException(f"Error listando archivos: {str(e)}", path=str(full_path))
    
    async def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Obtiene información de un archivo"""
        full_path = self._get_full_path(file_path)
        
        try:
            if not full_path.exists():
                raise StorageException("Archivo no encontrado", path=str(full_path))
            
            stat = full_path.stat()
            
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_file": full_path.is_file(),
                "is_dir": full_path.is_dir()
            }
            
        except StorageException:
            raise
        except Exception as e:
            logger.error("Error obteniendo info del archivo", path=str(full_path), error=str(e))
            raise StorageException(f"Error obteniendo info del archivo: {str(e)}", path=str(full_path))
    
    async def create_directory(self, directory: Path) -> None:
        """Crea un directorio"""
        full_path = self._get_full_path(directory)
        
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            logger.debug("Directorio creado", path=str(full_path))
            
        except Exception as e:
            logger.error("Error creando directorio", path=str(full_path), error=str(e))
            raise StorageException(f"Error creando directorio: {str(e)}", path=str(full_path))
    
    async def delete_directory(self, directory: Path, recursive: bool = False) -> None:
        """Elimina un directorio"""
        full_path = self._get_full_path(directory)
        
        try:
            if not full_path.exists():
                return
            
            if recursive:
                shutil.rmtree(full_path)
            else:
                full_path.rmdir()
            
            logger.debug("Directorio eliminado", path=str(full_path), recursive=recursive)
            
        except Exception as e:
            logger.error("Error eliminando directorio", path=str(full_path), error=str(e))
            raise StorageException(f"Error eliminando directorio: {str(e)}", path=str(full_path))
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del almacenamiento"""
        try:
            stat = shutil.disk_usage(self.base_path)
            
            return {
                "type": "local",
                "path": str(self.base_path),
                "total_space_gb": round(stat.total / (1024**3), 2),
                "used_space_gb": round(stat.used / (1024**3), 2),
                "free_space_gb": round(stat.free / (1024**3), 2),
                "usage_percentage": round((stat.used / stat.total) * 100, 2)
            }
            
        except Exception as e:
            logger.error("Error obteniendo estadísticas de almacenamiento", error=str(e))
            return {
                "type": "local",
                "path": str(self.base_path),
                "error": str(e)
            }
    
    async def move_file(self, source: Path, destination: Path) -> None:
        """Mueve un archivo a otra ubicación"""
        source_path = self._get_full_path(source)
        dest_path = self._get_full_path(destination)
        
        try:
            # Crear directorio destino si no existe
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Mover archivo
            shutil.move(str(source_path), str(dest_path))
            
            logger.debug("Archivo movido", source=str(source_path), destination=str(dest_path))
            
        except Exception as e:
            logger.error("Error moviendo archivo", source=str(source_path), destination=str(dest_path), error=str(e))
            raise StorageException(f"Error moviendo archivo: {str(e)}", path=str(source_path))
    
    async def copy_file(self, source: Path, destination: Path) -> None:
        """Copia un archivo a otra ubicación"""
        source_path = self._get_full_path(source)
        dest_path = self._get_full_path(destination)
        
        try:
            # Crear directorio destino si no existe
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copiar archivo
            shutil.copy2(str(source_path), str(dest_path))
            
            logger.debug("Archivo copiado", source=str(source_path), destination=str(dest_path))
            
        except Exception as e:
            logger.error("Error copiando archivo", source=str(source_path), destination=str(dest_path), error=str(e))
            raise StorageException(f"Error copiando archivo: {str(e)}", path=str(source_path))
