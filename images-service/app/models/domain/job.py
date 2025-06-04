"""
Modelo de dominio para Jobs
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field


class JobType(str, Enum):
    """Tipos de jobs disponibles"""
    DOWNLOAD_COLLECTION = "download_collection"
    DOWNLOAD_DOCUMENT = "download_document"
    DOWNLOAD_BATCH = "download_batch"
    PROCESS = "process"


class JobStatus(str, Enum):
    """Estados posibles de un job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobError:
    """Error ocurrido durante la ejecución de un job"""
    timestamp: datetime
    message: str
    error_type: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Job:
    """Modelo de dominio para un Job"""
    id: str
    type: JobType
    status: JobStatus
    database: str
    collection: str
    document_id: Optional[str] = None
    filter_query: Optional[Dict[str, Any]] = None
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[JobError] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Calcula el porcentaje de progreso"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def is_finished(self) -> bool:
        """Verifica si el job ha terminado"""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    @property
    def duration(self) -> Optional[float]:
        """Calcula la duración del job en segundos"""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    def add_error(self, message: str, error_type: str = "GenericError", details: Dict[str, Any] = None):
        """Añade un error al job"""
        error = JobError(
            timestamp=datetime.utcnow(),
            message=message,
            error_type=error_type,
            details=details or {}
        )
        self.errors.append(error)
        self.failed_items += 1
    
    def start(self):
        """Marca el job como iniciado"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete(self):
        """Marca el job como completado"""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
    
    def fail(self, error_message: str = None):
        """Marca el job como fallido"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        if error_message:
            self.add_error(error_message, "JobFailure")
    
    def cancel(self):
        """Marca el job como cancelado"""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el job a diccionario"""
        return {
            "_id": self.id,
            "type": self.type.value,
            "status": self.status.value,
            "database": self.database,
            "collection": self.collection,
            "document_id": self.document_id,
            "filter_query": self.filter_query,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "failed_items": self.failed_items,
            "progress_percentage": self.progress_percentage,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "metadata": self.metadata,
            "errors": [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "message": error.message,
                    "error_type": error.error_type,
                    "details": error.details
                }
                for error in self.errors
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Crea un Job desde un diccionario"""
        # Convertir strings a enums
        job_type = JobType(data["type"])
        job_status = JobStatus(data["status"])
        
        # Convertir timestamps
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"]
        started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        
        # Convertir errores
        errors = []
        for error_data in data.get("errors", []):
            error = JobError(
                timestamp=datetime.fromisoformat(error_data["timestamp"]) if isinstance(error_data["timestamp"], str) else error_data["timestamp"],
                message=error_data["message"],
                error_type=error_data["error_type"],
                details=error_data.get("details", {})
            )
            errors.append(error)
        
        return cls(
            id=data["_id"],
            type=job_type,
            status=job_status,
            database=data["database"],
            collection=data["collection"],
            document_id=data.get("document_id"),
            filter_query=data.get("filter_query"),
            total_items=data.get("total_items", 0),
            processed_items=data.get("processed_items", 0),
            failed_items=data.get("failed_items", 0),
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            metadata=data.get("metadata", {}),
            errors=errors
        )
