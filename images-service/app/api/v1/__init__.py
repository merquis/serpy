"""
API v1 del microservicio de imágenes
"""
from fastapi import APIRouter

from .endpoints import download, jobs, health, download_simple, serve

# Crear router principal de v1
api_router = APIRouter()

# Incluir routers de endpoints
api_router.include_router(download.router)
api_router.include_router(download_simple.router)
api_router.include_router(jobs.router)
api_router.include_router(health.router)
api_router.include_router(serve.router)

__all__ = ["api_router"]
