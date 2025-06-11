"""
Configuración centralizada del microservicio de imágenes
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
import re
from pathlib import Path


def normalize_project_name(project_name: str) -> str:
    """
    Normaliza el nombre del proyecto para usar como prefijo de colecciones
    
    Args:
        project_name: Nombre original del proyecto
        
    Returns:
        Nombre normalizado (a-z, 0-9, todo lo demás se convierte en _)
    """
    # Convertir a minúsculas
    normalized = project_name.lower()
    
    # Reemplazar todo lo que no sea a-z o 0-9 por guión bajo
    normalized = re.sub(r'[^a-z0-9]', '_', normalized)
    
    # Limpiar guiones bajos múltiples consecutivos
    normalized = re.sub(r'_+', '_', normalized)
    
    # Eliminar guiones bajos al inicio y final
    normalized = normalized.strip('_')
    
    return normalized


class Settings(BaseSettings):
    """Configuración principal del servicio"""
    
    # Application
    app_name: str = Field(default="images-service", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Project Configuration
    active_project: str = Field(default="TripToIslands", env="ACTIVE_PROJECT")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    api_key: str = Field(default="secure-api-key-here", env="API_KEY")
    cors_origins: List[str] = Field(
        default=["http://app.serpsrewrite.com", "http://localhost:8501"],
        env="CORS_ORIGINS"
    )
    
    # MongoDB
    mongodb_uri: str = Field(
        default="mongodb://mongo:27017",
        env="MONGODB_URI"
    )
    
    @property
    def mongodb_database(self) -> str:
        """Base de datos fija para todos los proyectos"""
        return "serpy"
    
    # Redis
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/0", env="CELERY_RESULT_BACKEND")
    
    # Storage
    storage_path: Path = Field(default=Path("/images"), env="STORAGE_PATH")
    storage_type: str = Field(default="local", env="STORAGE_TYPE")  # local o s3
    
    # Download Limits
    max_concurrent_downloads: int = Field(default=20, env="MAX_CONCURRENT_DOWNLOADS")
    max_connections_per_host: int = Field(default=10, env="MAX_CONNECTIONS_PER_HOST")
    download_timeout: int = Field(default=30, env="DOWNLOAD_TIMEOUT")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay: int = Field(default=1, env="RETRY_DELAY")
    
    # Processing (preparado para futuro)
    enable_webp_conversion: bool = Field(default=False, env="ENABLE_WEBP_CONVERSION")
    enable_optimization: bool = Field(default=False, env="ENABLE_OPTIMIZATION")
    jpeg_quality: int = Field(default=85, env="JPEG_QUALITY")
    webp_quality: int = Field(default=85, env="WEBP_QUALITY")
    
    # Webhook
    webhook_url: Optional[str] = Field(default=None, env="WEBHOOK_URL")
    
    @validator("storage_path", pre=True)
    def validate_storage_path(cls, v):
        """Convierte string a Path si es necesario"""
        if isinstance(v, str):
            return Path(v)
        return v
    
    @validator("cors_origins", pre=True)
    def validate_cors_origins(cls, v):
        """Parsea CORS origins desde string si viene de env"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def is_production(self) -> bool:
        """Verifica si está en producción"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Verifica si está en desarrollo"""
        return self.environment == "development"
    
    def get_storage_path(self, database: str, collection: str, document_id: str, search_field: str) -> Path:
        """Genera la ruta de almacenamiento para un documento"""
        sanitized_field = self.sanitize_filename(search_field)
        return self.storage_path / database / collection / f"{document_id}-{sanitized_field}"
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 100) -> str:
        """Sanitiza un nombre de archivo"""
        # Convertir a minúsculas
        filename = filename.lower()
        
        # Reemplazar espacios por guiones
        filename = filename.replace(" ", "-")
        
        # Eliminar caracteres especiales excepto guiones
        import re
        filename = re.sub(r'[^a-z0-9\-]', '', filename)
        
        # Eliminar guiones múltiples
        filename = re.sub(r'-+', '-', filename)
        
        # Eliminar guiones al inicio y final
        filename = filename.strip('-')
        
        # Limitar longitud
        if len(filename) > max_length:
            filename = filename[:max_length]
        
        # Si queda vacío, usar un valor por defecto
        if not filename:
            filename = "unnamed"
        
        return filename
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()
