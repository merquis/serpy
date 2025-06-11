"""
Configuración centralizada del proyecto SERPY API

Este módulo gestiona toda la configuración de la API de forma centralizada.
Utiliza Pydantic Settings para una gestión robusta de variables de entorno.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, List, Optional
import os
import re
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    """Configuración principal del servicio API"""
    
    # Application
    app_name: str = Field(default="SERPY API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(
        default="API REST para acceder a las colecciones de MongoDB de SERPY",
        env="APP_DESCRIPTION"
    )
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Project Configuration
    active_project: str = Field(default="TripToIslands", env="ACTIVE_PROJECT")
    
    # MongoDB
    mongodb_uri: str = Field(
        default="mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin",
        env="MONGO_URI"
    )
    
    @property
    def mongodb_database(self) -> str:
        """Base de datos fija para todos los proyectos"""
        return "serpy"
    
    # API
    api_base_url: str = Field(default="https://api.serpsrewrite.com", env="API_BASE_URL")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    
    # Colecciones disponibles (se cargarán dinámicamente de MongoDB)
    available_collections: Optional[List[str]] = None
    
    # Configuración de paginación
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # CORS
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    cors_methods: List[str] = Field(default=["*"], env="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], env="CORS_HEADERS")
    
    @property
    def is_production(self) -> bool:
        """Verifica si está en producción"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Verifica si está en desarrollo"""
        return self.environment == "development"
    
    @staticmethod
    def collection_to_slug(collection_name: str) -> str:
        """Convierte el nombre de una colección a su slug para URLs"""
        return collection_name.lower().replace(" ", "-")
    
    @staticmethod
    def slug_to_collection(slug: str, available_collections: List[str]) -> Optional[str]:
        """Convierte un slug de URL al nombre real de la colección"""
        # Primero buscar coincidencia exacta (para colecciones que ya son minúsculas)
        if slug in available_collections:
            return slug
        
        # Luego buscar la colección que coincida con el slug
        for collection in available_collections:
            if Settings.collection_to_slug(collection) == slug:
                return collection
        return None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()

# Log de configuración inicial
logger.info(f"Configuración cargada - Entorno: {settings.environment}")
logger.info(f"Base de datos: {settings.mongodb_database}")
