"""
Excepciones personalizadas para el microservicio
"""
from typing import Optional, Dict, Any


class ImagesServiceException(Exception):
    """Excepción base para el servicio de imágenes"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para respuestas API"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "status_code": self.status_code
        }


class DownloadException(ImagesServiceException):
    """Excepción para errores de descarga"""
    
    def __init__(self, message: str, url: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if url:
            details["url"] = url
        kwargs["details"] = details
        super().__init__(message, error_code="DOWNLOAD_ERROR", **kwargs)


class StorageException(ImagesServiceException):
    """Excepción para errores de almacenamiento"""
    
    def __init__(self, message: str, path: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if path:
            details["path"] = path
        kwargs["details"] = details
        super().__init__(message, error_code="STORAGE_ERROR", **kwargs)


class DatabaseException(ImagesServiceException):
    """Excepción para errores de base de datos"""
    
    def __init__(self, message: str, collection: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if collection:
            details["collection"] = collection
        kwargs["details"] = details
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)


class ValidationException(ImagesServiceException):
    """Excepción para errores de validación"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        kwargs["details"] = details
        kwargs["status_code"] = 400
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class AuthenticationException(ImagesServiceException):
    """Excepción para errores de autenticación"""
    
    def __init__(self, message: str = "Authentication required", **kwargs):
        kwargs["status_code"] = 401
        super().__init__(message, error_code="AUTHENTICATION_ERROR", **kwargs)


class AuthorizationException(ImagesServiceException):
    """Excepción para errores de autorización"""
    
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        kwargs["status_code"] = 403
        super().__init__(message, error_code="AUTHORIZATION_ERROR", **kwargs)


class NotFoundException(ImagesServiceException):
    """Excepción para recursos no encontrados"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        kwargs["details"] = details
        kwargs["status_code"] = 404
        super().__init__(message, error_code="NOT_FOUND", **kwargs)


class JobException(ImagesServiceException):
    """Excepción para errores relacionados con jobs"""
    
    def __init__(self, message: str, job_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if job_id:
            details["job_id"] = job_id
        kwargs["details"] = details
        super().__init__(message, error_code="JOB_ERROR", **kwargs)


class RateLimitException(ImagesServiceException):
    """Excepción para límites de tasa excedidos"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get("details", {})
        if retry_after:
            details["retry_after"] = retry_after
        kwargs["details"] = details
        kwargs["status_code"] = 429
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", **kwargs)


class ProcessingException(ImagesServiceException):
    """Excepción para errores de procesamiento de imágenes"""
    
    def __init__(self, message: str, image_path: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if image_path:
            details["image_path"] = image_path
        kwargs["details"] = details
        super().__init__(message, error_code="PROCESSING_ERROR", **kwargs)
