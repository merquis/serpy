"""
Modelo de dominio para Imágenes y Metadata
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import hashlib


@dataclass
class ImageInfo:
    """Información de una imagen individual"""
    filename: str
    url: str
    size_bytes: int
    mime_type: str
    width: int
    height: int
    hash: str
    downloaded_at: datetime
    error: Optional[str] = None
    
    @property
    def size_mb(self) -> float:
        """Tamaño en megabytes"""
        return self.size_bytes / (1024 * 1024)
    
    @property
    def aspect_ratio(self) -> float:
        """Ratio de aspecto de la imagen"""
        if self.height == 0:
            return 0
        return self.width / self.height
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "filename": self.filename,
            "url": self.url,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_mb, 2),
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": round(self.aspect_ratio, 2),
            "hash": self.hash,
            "downloaded_at": self.downloaded_at.isoformat(),
            "error": self.error
        }


@dataclass
class ProcessedImages:
    """Imágenes procesadas en diferentes formatos"""
    webp: List[ImageInfo] = field(default_factory=list)
    thumbnail: List[ImageInfo] = field(default_factory=list)
    optimized: List[ImageInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convierte a diccionario"""
        return {
            "webp": [img.to_dict() for img in self.webp],
            "thumbnail": [img.to_dict() for img in self.thumbnail],
            "optimized": [img.to_dict() for img in self.optimized]
        }


@dataclass
class ImageMetadata:
    """Metadata completa de imágenes de un documento"""
    document_id: str
    collection: str
    database: str
    search_field: str
    search_field_sanitized: str
    original_images: List[ImageInfo] = field(default_factory=list)
    processed_images: ProcessedImages = field(default_factory=ProcessedImages)
    job_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def total_images(self) -> int:
        """Total de imágenes originales"""
        return len(self.original_images)
    
    @property
    def total_size_bytes(self) -> int:
        """Tamaño total en bytes"""
        return sum(img.size_bytes for img in self.original_images if not img.error)
    
    @property
    def total_size_mb(self) -> float:
        """Tamaño total en megabytes"""
        return self.total_size_bytes / (1024 * 1024)
    
    @property
    def failed_downloads(self) -> int:
        """Número de descargas fallidas"""
        return sum(1 for img in self.original_images if img.error)
    
    @property
    def successful_downloads(self) -> int:
        """Número de descargas exitosas"""
        return sum(1 for img in self.original_images if not img.error)
    
    def add_original_image(self, image_info: ImageInfo):
        """Añade una imagen original"""
        self.original_images.append(image_info)
        self.updated_at = datetime.utcnow()
    
    def add_processed_image(self, image_info: ImageInfo, format_type: str):
        """Añade una imagen procesada"""
        if format_type == "webp":
            self.processed_images.webp.append(image_info)
        elif format_type == "thumbnail":
            self.processed_images.thumbnail.append(image_info)
        elif format_type == "optimized":
            self.processed_images.optimized.append(image_info)
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para almacenar"""
        return {
            "document_id": self.document_id,
            "collection": self.collection,
            "database": self.database,
            "search_field": self.search_field,
            "search_field_sanitized": self.search_field_sanitized,
            "images": {
                "original": [img.to_dict() for img in self.original_images],
                "processed": self.processed_images.to_dict()
            },
            "statistics": {
                "total_images": self.total_images,
                "successful_downloads": self.successful_downloads,
                "failed_downloads": self.failed_downloads,
                "total_size_bytes": self.total_size_bytes,
                "total_size_mb": round(self.total_size_mb, 2)
            },
            "job_id": self.job_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageMetadata":
        """Crea desde un diccionario"""
        # Convertir imágenes originales
        original_images = []
        for img_data in data.get("images", {}).get("original", []):
            img = ImageInfo(
                filename=img_data["filename"],
                url=img_data["url"],
                size_bytes=img_data["size_bytes"],
                mime_type=img_data["mime_type"],
                width=img_data["width"],
                height=img_data["height"],
                hash=img_data["hash"],
                downloaded_at=datetime.fromisoformat(img_data["downloaded_at"]),
                error=img_data.get("error")
            )
            original_images.append(img)
        
        # Convertir imágenes procesadas
        processed = ProcessedImages()
        processed_data = data.get("images", {}).get("processed", {})
        
        for format_type in ["webp", "thumbnail", "optimized"]:
            images = []
            for img_data in processed_data.get(format_type, []):
                img = ImageInfo(
                    filename=img_data["filename"],
                    url=img_data["url"],
                    size_bytes=img_data["size_bytes"],
                    mime_type=img_data["mime_type"],
                    width=img_data["width"],
                    height=img_data["height"],
                    hash=img_data["hash"],
                    downloaded_at=datetime.fromisoformat(img_data["downloaded_at"]),
                    error=img_data.get("error")
                )
                images.append(img)
            
            setattr(processed, format_type, images)
        
        return cls(
            document_id=data["document_id"],
            collection=data["collection"],
            database=data["database"],
            search_field=data["search_field"],
            search_field_sanitized=data["search_field_sanitized"],
            original_images=original_images,
            processed_images=processed,
            job_id=data.get("job_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


def calculate_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """
    Calcula el hash de un archivo
    
    Args:
        file_path: Ruta del archivo
        algorithm: Algoritmo de hash (md5, sha1, sha256)
        
    Returns:
        Hash del archivo en hexadecimal
    """
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def calculate_bytes_hash(data: bytes, algorithm: str = "md5") -> str:
    """
    Calcula el hash de datos en bytes
    
    Args:
        data: Datos en bytes
        algorithm: Algoritmo de hash (md5, sha1, sha256)
        
    Returns:
        Hash en hexadecimal
    """
    hash_func = getattr(hashlib, algorithm)()
    hash_func.update(data)
    return hash_func.hexdigest()
