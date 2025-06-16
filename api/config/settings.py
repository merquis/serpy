from typing import List
from pydantic import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Serpy"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "serpy_db"
    N8N_WEBHOOK_URL: str = "https://n8n.serpsrewrite.com/webhook/publicar-hotel"

    class Config:
        env_file = ".env"

settings = Settings()

def normalize_project_name(project_name: str) -> str:
    """Normaliza el nombre del proyecto para usarlo en nombres de colecciones"""
    import re
    name = project_name.lower()
    name = re.sub(r'[^a-z0-9\-_]', '', name)
    return name

def get_collection_name(project_name: str, suffix: str) -> str:
    """Crea un nombre de colección combinando el nombre del proyecto y un sufijo"""
    normalized_name = normalize_project_name(project_name)
    return f"{normalized_name}_{suffix}"
