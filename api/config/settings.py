"""
Configuración centralizada del proyecto SERPY API
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import os
import json
from pathlib import Path


@dataclass
class AppConfig:
    """Configuración general de la aplicación API"""
    app_name: str = "SERPY API"
    app_version: str = "1.0.0"
    app_description: str = "API REST para acceder a las colecciones de MongoDB de SERPY"
    
    # MongoDB
    mongo_default_db: str = "serpy"
    
    # API
    api_base_url: str = "https://serpy.videocursosweb.com"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Colecciones disponibles
    available_collections: List[str] = None
    
    # Configuración de paginación
    default_page_size: int = 20
    max_page_size: int = 100
    
    def __post_init__(self):
        if self.available_collections is None:
            self.available_collections = [
                "urls_google",
                "urls_google_tags",
                "hoteles",
                "posts"
            ]


@dataclass
class SecurityConfig:
    """Configuración de seguridad"""
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
    """Clase principal de configuración"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.app = AppConfig()
            cls._instance.security = SecurityConfig()
            cls._instance._load_secrets()
        return cls._instance
    
    def _load_secrets(self):
        """Carga los secretos desde variables de entorno o archivo de configuración"""
        # Intentar cargar desde archivo secrets.json si existe
        secrets_file = Path(__file__).parent.parent / "secrets.json"
        if secrets_file.exists():
            try:
                with open(secrets_file, 'r') as f:
                    self._secrets = json.load(f)
            except Exception:
                self._secrets = {}
        else:
            self._secrets = {}
    
    @property
    def mongo_uri(self) -> str:
        """Obtiene la URI de MongoDB desde variables de entorno o secretos"""
        # Primero intentar variable de entorno
        env_uri = os.getenv("MONGO_URI")
        if env_uri:
            return env_uri
        
        # Luego intentar desde secretos
        if "mongodb" in self._secrets and "uri" in self._secrets["mongodb"]:
            return self._secrets["mongodb"]["uri"]
        
        # Valor por defecto genérico
        return "mongodb://localhost:27017/"
    
    @property
    def environment(self) -> str:
        """Obtiene el entorno de ejecución"""
        return os.getenv("ENVIRONMENT", "development")
    
    @property
    def debug(self) -> bool:
        """Determina si está en modo debug"""
        return self.environment == "development"


# Instancia global de configuración
config = Config()
