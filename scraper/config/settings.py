"""
Configuración centralizada del proyecto SERPY
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, List, Optional, Any
import streamlit as st
from pathlib import Path
import os
import re


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


def get_collection_name(project_name: str, suffix_key: str) -> str:
    """
    Genera el nombre de colección completo usando el proyecto y el sufijo
    
    Args:
        project_name: Nombre del proyecto
        suffix_key: Clave del sufijo en collection_suffixes
        
    Returns:
        Nombre completo de la colección (ej: "triptoislands_urls_google")
    """
    from config.settings import settings
    
    normalized_project = normalize_project_name(project_name)
    suffix = settings.collection_suffixes.get(suffix_key, f"_{suffix_key}")
    
    return f"{normalized_project}{suffix}"


class Settings(BaseSettings):
    """Configuración principal del servicio Scraper"""
    N8N_WEBHOOK_URL: str = "https://n8n-n8n.hpv7eo.easypanel.host/webhook-test/publicar-hotel"
    
    # Application
    app_name: str = Field(default="SERPY Admin", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    page_title: str = Field(default="SERPY - Herramienta SEO Profesional", env="PAGE_TITLE")
    layout: str = Field(default="wide", env="LAYOUT")
    initial_sidebar_state: str = Field(default="expanded", env="INITIAL_SIDEBAR_STATE")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Project Configuration
    active_project: str = Field(default="TripToIslands", env="ACTIVE_PROJECT")
    default_project_name: str = Field(default="TripToIslands", env="DEFAULT_PROJECT_NAME")
    
    # MongoDB
    mongodb_uri: str = Field(
        default="mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin",
        env="MONGODB_URI"
    )
    mongo_default_collection: str = Field(default="hoteles", env="MONGO_DEFAULT_COLLECTION")
    
    @property
    def mongodb_database(self) -> str:
        """Base de datos fija para todos los proyectos"""
        return "serpy"
    
    def get_project_from_secrets(self) -> str:
        """Obtiene el proyecto activo desde Streamlit secrets"""
        try:
            return st.secrets.get("project", {}).get("active", self.active_project)
        except:
            return self.active_project
    
    # Google Drive
    drive_root_folder_id: str = Field(
        default="1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy", 
        env="DRIVE_ROOT_FOLDER_ID"
    )
    
    # Límites y configuraciones
    max_scraping_results: int = Field(default=100, env="MAX_SCRAPING_RESULTS")
    default_scraping_results: int = Field(default=10, env="DEFAULT_SCRAPING_RESULTS")
    max_h2_titles: int = Field(default=500, env="MAX_H2_TITLES")
    max_h3_titles: int = Field(default=500, env="MAX_H3_TITLES")
    
    # Modelos de IA disponibles por proveedor
    ai_providers: Dict[str, Dict[str, Any]] = Field(
        default={
            "OpenAI": {
                "models": [
                    "gpt-4.1-mini-2025-04-14",
                    "gpt-4.1-2025-04-14", 
                    "chatgpt-4o-latest",
                    "o3-2025-04-16",
                    "o3-mini-2025-04-16",
                ],
                "default": "gpt-4.1-mini-2025-04-14"
            },
            "Claude": {
                "models": [
                    "claude-opus-4-20250514",
                    "claude-sonnet-4-20250514",
                    "claude-3-7-sonnet-20250219",
                    "claude-3-7-sonnet-latest",
                    "claude-3-5-haiku-20241022",
                    "claude-3-5-haiku-latest"
                ],
                "default": "claude-3-5-haiku-latest"
            },
            "Google Gemini": {
                "models": [
                    "gemini-2.0-flash",
                    "gemini-2.5-flash-preview-05-20",
                    "gemini-2.5-pro-preview-06-05"
                ],
                "default": "gemini-2.0-flash"
            }
        }
    )
    
    # Mantener compatibilidad con código existente
    @property
    def gpt_models(self) -> List[str]:
        """Lista de modelos GPT para compatibilidad con código existente"""
        return self.ai_providers["OpenAI"]["models"]
    
    # Scraping Configuration
    step_size: int = Field(default=10, env="STEP_SIZE")
    timeout: int = Field(default=30, env="TIMEOUT")
    
    # Google Domains
    google_domains: Dict[str, str] = Field(
        default={
            "Global (.com)": "google.com",
            "España (.es)": "google.es",
            "Reino Unido (.co.uk)": "google.co.uk",
            "Alemania (.de)": "google.de",
            "Francia (.fr)": "google.fr"
        }
    )
    
    # Search Languages
    search_languages: Dict[str, tuple] = Field(
        default={
            "Español (España)": ("es", "es"),
            "Inglés (UK)": ("en-GB", "uk"),
            "Alemán (Alemania)": ("de", "de"),
            "Francés (Francia)": ("fr", "fr")
        }
    )
    
    # UI Configuration
    primary_color: str = Field(default="#FF6B6B", env="PRIMARY_COLOR")
    background_color: str = Field(default="#FAFAFA", env="BACKGROUND_COLOR")
    secondary_background_color: str = Field(default="#F0F2F6", env="SECONDARY_BACKGROUND_COLOR")
    text_color: str = Field(default="#262730", env="TEXT_COLOR")
    
    # Iconos
    icons: Dict[str, str] = Field(
        default={
            "search": "🔍",
            "download": "⬇️",
            "upload": "☁️",
            "folder": "📁",
            "document": "📄",
            "settings": "⚙️",
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "loading": "🔄",
            "robot": "🤖",
            "chart": "📊",
            "clean": "🧹",
            "run": "🚀"
        }
    )
    
    # Sufijos de colecciones MongoDB por proyecto
    # Cada sufijo se combina con el nombre del proyecto normalizado para crear colecciones dinámicas
    # Ejemplo: proyecto "TriptoIslands" → colección "triptoislands_urls_google"
    collection_suffixes: Dict[str, str] = Field(
        default={
            # Botones principales (cada uno corresponde a un botón de la interfaz)
            "buscar_google": "_urls_google",                    # Buscar en Google (sin checkboxes)
            "extraer_datos_web_google": "_urls_google_tags",    # Extraer datos web Google
            "buscar_hoteles_booking": "_urls_booking",          # Buscar hoteles Booking (sin checkboxes)
            "extraer_hoteles_booking": "_hoteles_booking_urls", # Extraer hoteles Booking
            "generador_articulos": "_posts",                    # Generador de artículos
            "booking_extracted": "_hotel-booking",             # Buscar hoteles Booking + checkbox "Extraer información URLs"
        }
    )
    
    @property
    def is_production(self) -> bool:
        """Verifica si está en producción"""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Verifica si está en desarrollo"""
        return self.environment == "development"
    
    @property
    def secrets(self):
        """Acceso seguro a los secretos de Streamlit"""
        return st.secrets
    
    @property
    def openai_api_key(self) -> str:
        """Obtiene la API key de OpenAI desde Streamlit secrets"""
        return st.secrets["openai"]["api_key"]
    
    @property
    def claude_api_key(self) -> str:
        """Obtiene la API key de Claude desde Streamlit secrets"""
        return st.secrets["claude"]["api_key"]
    
    @property
    def gemini_api_key(self) -> str:
        """Obtiene la API key de Gemini desde Streamlit secrets"""
        return st.secrets["gemini"]["api_key"]
    
    @property
    def brightdata_token(self) -> str:
        """Obtiene el token de BrightData desde Streamlit secrets"""
        return st.secrets["brightdata"]["token"]
    
    @property
    def mongo_uri(self) -> str:
        """Obtiene la URI de MongoDB desde Streamlit secrets"""
        try:
            # Intentar obtener desde secrets
            return st.secrets["mongodb"]["uri"]
        except:
            # Si no hay secrets, usar la configuración por defecto
            return self.mongodb_uri
    
    @property
    def drive_credentials(self) -> dict:
        """Obtiene las credenciales de Google Drive desde Streamlit secrets"""
        return dict(st.secrets["drive_service_account"])
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Instancia global de configuración
settings = Settings()
