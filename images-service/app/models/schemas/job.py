"""
Schemas Pydantic para Jobs en la API
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator

from app.models.domain import JobType, JobStatus


class JobCreateRequest(BaseModel):
    """Schema para crear un nuevo job"""
    type: JobType
    database: str = Field(..., description="Base de datos MongoDB")
    collection: str = Field(..., description="Colección MongoDB")
    document_id: Optional[str] = Field(None, description="ID del documento específico")
    filter_query: Optional[Dict[str, Any]] = Field(None, description="Filtro MongoDB para batch")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata adicional")
    
    @validator("database", "collection")
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("No puede estar vacío")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "download_collection",
                "database": "serpy_db",
                "collection": "hotels",
                "metadata": {
                    "priority": "high",
                    "source": "api"
                }
            }
        }


class JobErrorResponse(BaseModel):
    """Schema para errores en jobs"""
    timestamp: datetime
    message: str
    error_type: str
    details: Dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    """Schema para respuesta de job"""
    id: str = Field(..., alias="_id")
    type: JobType
    status: JobStatus
    database: str
    collection: str
    document_id: Optional[str] = None
    filter_query: Optional[Dict[str, Any]] = None
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    progress_percentage: float = 0.0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: List[JobErrorResponse] = Field(default_factory=list)
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "507f1f77bcf86cd799439011",
                "type": "download_collection",
                "status": "running",
                "database": "serpy_db",
                "collection": "hotels",
                "total_items": 100,
                "processed_items": 45,
                "failed_items": 2,
                "progress_percentage": 45.0,
                "created_at": "2024-01-01T10:00:00Z",
                "started_at": "2024-01-01T10:01:00Z",
                "duration": 120.5,
                "metadata": {"priority": "high"},
                "errors": []
            }
        }


class JobListResponse(BaseModel):
    """Schema para listado de jobs"""
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [],
                "total": 50,
                "page": 1,
                "page_size": 20,
                "total_pages": 3
            }
        }


class JobCancelRequest(BaseModel):
    """Schema para cancelar un job"""
    reason: Optional[str] = Field(None, description="Razón de cancelación")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Cancelado por el usuario"
            }
        }


class BatchDownloadRequest(BaseModel):
    """Schema para descarga batch con filtros custom"""
    database: str = Field(..., description="Base de datos MongoDB")
    collection: str = Field(..., description="Colección MongoDB")
    filter: Dict[str, Any] = Field(..., description="Filtro MongoDB")
    limit: Optional[int] = Field(None, description="Límite de documentos", ge=1)
    skip: Optional[int] = Field(None, description="Documentos a saltar", ge=0)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "database": "serpy_db",
                "collection": "hotels",
                "filter": {
                    "city": "Madrid",
                    "rating": {"$gte": 4}
                },
                "limit": 50,
                "skip": 0
            }
        }
