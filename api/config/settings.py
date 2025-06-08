"""
Configuración centralizada del proyecto SERPY API

Este módulo gestiona toda la configuración de la API de forma centralizada.
Utiliza dataclasses para estructurar la configuración y carga todos los
valores desde variables de entorno.

Componentes principales:
- AppConfig: Configuración general de la aplicación
- SecurityConfig: Configuración de seguridad y CORS
- Config: Clase principal que gestiona toda la configuración
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import os
import json
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """
    Configuración general de la aplicación API.
    
    Attributes:
        app_name: Nombre de la aplicación
        app_version: Versión de la API
        app_description: Descripción de la API
        mongo_default_db: Base de datos MongoDB por defecto
        api_base_url: URL base de la API en producción
        api_host: Host donde escucha la API
        api_port: Puerto donde escucha la API
        available_collections: Lista de colecciones (se carga dinámicamente)
        default_page_size: Tamaño de página por defecto
        max_page_size: Tamaño máximo de página permitido
    """
    app_name: str = "SERPY API"
    app_version: str = "1.0.0"
    app_description: str = "API REST para acceder a las colecciones de MongoDB de SERPY"
    
    # MongoDB
    mongo_default_db: str = "serpy"
    
    # API
    api_base_url: str = "https://api.serpsrewrite.com"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Colecciones disponibles (se cargarán dinámicamente de MongoDB)
    available_collections: List[str] = None
    
    # Configuración de paginación
    default_page_size: int = 20
    max_page_size: int = 100
    
    def __post_init__(self):
        # Las colecciones se cargarán dinámicamente desde MongoDB
        pass
    
    @staticmethod
    def collection_to_slug(collection_name: str) -> str:
        """Convierte el nombre de una colección a su slug para URLs"""
        # Convertir a minúsculas y reemplazar espacios por guiones
        return collection_name.lower().replace(" ", "-")
    
    @staticmethod
    def slug_to_collection(slug: str, available_collections: List[str]) -> Optional[str]:
        """Convierte un slug de URL al nombre real de la colección"""
        # Primero buscar coincidencia exacta (para colecciones que ya son minúsculas)
        if slug in available_collections:
            return slug
        
        # Luego buscar la colección que coincida con el slug
        for collection in available_collections:
            if AppConfig.collection_to_slug(collection) == slug:
                return collection
        return None


@dataclass
class SecurityConfig:
    """
    Configuración de seguridad de la API.
    
    Gestiona principalmente la configuración CORS para permitir
    acceso desde diferentes orígenes.
    
    Attributes:
        cors_origins: Lista de orígenes permitidos
        cors_credentials: Si se permiten credenciales
        cors_methods: Métodos HTTP permitidos
        cors_headers: Headers permitidos
    """
    # CORS
    cors_origins: List[str] = None
    cors_credentials: bool = True
    cors_methods: List[str] = None
    cors_headers: List[str] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]
        if self.cors_methods is None:
            self.cors_methods = ["*"]
        if self.cors_headers is None:
            self.cors_headers = ["*"]


class Config:
    """
    Clase principal de configuración (Singleton).
    
    Implementa el patrón Singleton para asegurar una única instancia
    de configuración en toda la aplicación. Gestiona la carga de
    configuración desde variables de entorno y archivos de secretos.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.app = AppConfig()
            cls._instance.security = SecurityConfig()
            cls._instance._load_secrets()
        return cls._instance
    
    def _load_secrets(self):
        """
        Carga los secretos desde variables de entorno.
        
        Este método existe por compatibilidad pero ya no carga archivos JSON.
        Toda la configuración debe venir de variables de entorno.
        """
        self._secrets = {}
        logger.info("Configuración cargada desde variables de entorno")
    
    @property
    def mongo_uri(self) -> str:
        """
        Obtiene la URI de MongoDB desde variables de entorno.
        
        Returns:
            str: URI de conexión a MongoDB
        """
        # Obtener de variable de entorno
        env_uri = os.getenv("MONGO_URI")
        if env_uri:
            logger.info(f"Usando MONGO_URI desde variable de entorno")
            # Log parcial de la URI para debugging (ocultando la contraseña)
            if "@" in env_uri:
                parts = env_uri.split("@")
                safe_uri = parts[0].split("//")[0] + "//***:***@" + parts[1]
                logger.info(f"Conectando a: {safe_uri}")
            return env_uri
        
        # Valor por defecto - usar el mismo que el scraper
        logger.warning("No se encontró MONGO_URI, usando valor por defecto del scraper")
        return "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"
    
    @property
    def environment(self) -> str:
        """
        Obtiene el entorno de ejecución.
        
        Returns:
            str: 'development' o 'production'
        """
        return os.getenv("ENVIRONMENT", "development")
    
    @property
    def debug(self) -> bool:
        """
        Determina si está en modo debug.
        
        Returns:
            bool: True si está en desarrollo, False en producción
        """
        return self.environment == "development"


# Instancia global de configuración
config = Config()

# Log de configuración inicial
logger.info(f"Configuración cargada - Entorno: {config.environment}")
logger.info(f"Base de datos: {config.app.mongo_default_db}")
