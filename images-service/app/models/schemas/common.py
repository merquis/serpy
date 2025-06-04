"""
Schemas Pydantic comunes para la API
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    """Schema para health check"""
    status: str = Field(..., description="Estado del servicio")
    service: str = Field(..., description="Nombre del servicio")
    version: str = Field(..., description="Versión del servicio")
    environment: str = Field(..., description="Entorno de ejecución")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    database: Optional[str] = Field(None, description="Estado de la base de datos")
    redis: Optional[str] = Field(None, description="Estado de Redis")
    storage: Optional[Dict[str, Any]] = Field(None, description="Estado del almacenamiento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "images-service",
                "version": "1.0.0",
                "environment": "production",
                "timestamp": "2024-01-01T10:00:00Z",
                "database": "connected",
                "redis": "connected",
                "storage": {
                    "type": "local",
                    "path": "/images",
                    "available_space_gb": 450.5
                }
            }
        }


class MetricsResponse(BaseModel):
    """Schema para métricas Prometheus"""
    metrics: str = Field(..., description="Métricas en formato Prometheus")
    
    class Config:
        json_schema_extra = {
            "example": {
                "metrics": "# HELP images_downloaded_total Total number of images downloaded\n# TYPE images_downloaded_total counter\nimages_downloaded_total 1234"
            }
        }


class ErrorResponse(BaseModel):
    """Schema para respuestas de error"""
    error: str = Field(..., description="Código de error")
    message: str = Field(..., description="Mensaje de error")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalles adicionales del error")
    status_code: int = Field(..., description="Código de estado HTTP")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "El campo 'collection' es requerido",
                "details": {
                    "field": "collection",
                    "value": None
                },
                "status_code": 400,
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }


class SuccessResponse(BaseModel):
    """Schema para respuestas exitosas genéricas"""
    success: bool = True
    message: str = Field(..., description="Mensaje de éxito")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operación completada exitosamente",
                "data": {
                    "affected_items": 10
                },
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }


class PaginationParams(BaseModel):
    """Schema para parámetros de paginación"""
    page: int = Field(1, ge=1, description="Número de página")
    page_size: int = Field(20, ge=1, le=100, description="Tamaño de página")
    
    @property
    def skip(self) -> int:
        """Calcula el número de elementos a saltar"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias para page_size"""
        return self.page_size


class WebhookPayload(BaseModel):
    """Schema para payload de webhook"""
    event: str = Field(..., description="Tipo de evento")
    job_id: str = Field(..., description="ID del job")
    status: str = Field(..., description="Estado del job")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(..., description="Datos del evento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event": "job.completed",
                "job_id": "507f1f77bcf86cd799439011",
                "status": "completed",
                "timestamp": "2024-01-01T10:00:00Z",
                "data": {
                    "total_items": 100,
                    "processed_items": 98,
                    "failed_items": 2,
                    "duration": 300.5
                }
            }
        }


class ImageDownloadStats(BaseModel):
    """Schema para estadísticas de descarga"""
    total_images: int = Field(..., description="Total de imágenes")
    successful_downloads: int = Field(..., description="Descargas exitosas")
    failed_downloads: int = Field(..., description="Descargas fallidas")
    total_size_mb: float = Field(..., description="Tamaño total en MB")
    average_size_mb: float = Field(..., description="Tamaño promedio por imagen en MB")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_images": 100,
                "successful_downloads": 98,
                "failed_downloads": 2,
                "total_size_mb": 245.5,
                "average_size_mb": 2.5
            }
        }
