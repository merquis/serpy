"""
Servicios de almacenamiento
"""
from .base import StorageService
from .local_storage import LocalStorageService

__all__ = ["StorageService", "LocalStorageService"]
