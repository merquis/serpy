"""
Configuración centralizada del proyecto SERPY
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import streamlit as st
from pathlib import Path

@dataclass
class AppConfig:
    """Configuración general de la aplicación"""
    app_name: str = "SERPY Admin"
    page_title: str = "SERPY - Herramienta SEO Profesional"
    layout: str = "wide"
    initial_sidebar_state: str = "expanded"
    
    # Carpetas de Google Drive
    drive_root_folder_id: str = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    default_project_name: str = "TripToIslands"
    
    # MongoDB
    mongo_default_db: str = "serpy"
    mongo_default_collection: str = "hoteles"
    
    # Límites y configuraciones
    max_scraping_results: int = 100
    default_scraping_results: int = 10
    max_h2_titles: int = 500
    max_h3_titles: int = 500
    
    # Modelos GPT disponibles
    gpt_models: List[str] = None
    
    def __post_init__(self):
        if self.gpt_models is None:
            self.gpt_models = [
                "gpt-4.1-mini-2025-04-14",
                "gpt-4.1-2025-04-14",
                "chatgpt-4o-latest",
                "o3-2025-04-16",
                "o3-mini-2025-04-16",
            ]

@dataclass
class ScrapingConfig:
    """Configuración para módulos de scraping"""
    google_domains: Dict[str, str] = None
    search_languages: Dict[str, tuple] = None
    step_size: int = 10
    timeout: int = 30
    
    def __post_init__(self):
        if self.google_domains is None:
            self.google_domains = {
                "Global (.com)": "google.com",
                "España (.es)": "google.es",
                "Reino Unido (.co.uk)": "google.co.uk",
                "Alemania (.de)": "google.de",
                "Francia (.fr)": "google.fr"
            }
        
        if self.search_languages is None:
            self.search_languages = {
                "Español (España)": ("es", "es"),
                "Inglés (UK)": ("en-GB", "uk"),
                "Alemán (Alemania)": ("de", "de"),
                "Francés (Francia)": ("fr", "fr")
            }

@dataclass
class UIConfig:
    """Configuración de interfaz de usuario"""
    # Colores del tema
    primary_color: str = "#FF6B6B"
    background_color: str = "#FAFAFA"
    secondary_background_color: str = "#F0F2F6"
    text_color: str = "#262730"
    
    # Iconos
    icons: Dict[str, str] = None
    
    def __post_init__(self):
        if self.icons is None:
            self.icons = {
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

class Config:
    """Clase principal de configuración"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.app = AppConfig()
            cls._instance.scraping = ScrapingConfig()
            cls._instance.ui = UIConfig()
        return cls._instance
    
    @property
    def secrets(self):
        """Acceso seguro a los secretos de Streamlit"""
        return st.secrets
    
    @property
    def openai_api_key(self) -> str:
        return st.secrets["openai"]["api_key"]
    
    @property
    def brightdata_token(self) -> str:
        return st.secrets["brightdata"]["token"]
    
    @property
    def mongo_uri(self) -> str:
        return st.secrets.get("mongodb", {}).get("uri", 
            "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin")
    
    @property
    def drive_credentials(self) -> dict:
        return dict(st.secrets["drive_service_account"])

# Instancia global de configuración
config = Config() 