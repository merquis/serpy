"""
Schemas Pydantic para la API
"""
from .job import (
    JobCreateRequest, JobResponse, JobListResponse, 
    JobCancelRequest, BatchDownloadRequest, JobErrorResponse
)
from .common import (
    HealthResponse, MetricsResponse, ErrorResponse, 
    SuccessResponse, PaginationParams, WebhookPayload,
    ImageDownloadStats
)

__all__ = [
    # Job schemas
    "JobCreateRequest", "JobResponse", "JobListResponse",
    "JobCancelRequest", "BatchDownloadRequest", "JobErrorResponse",
    # Common schemas
    "HealthResponse", "MetricsResponse", "ErrorResponse",
    "SuccessResponse", "PaginationParams", "WebhookPayload",
    "ImageDownloadStats"
]
