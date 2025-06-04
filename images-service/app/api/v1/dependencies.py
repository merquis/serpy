"""
Dependencias compartidas para los endpoints de la API
"""
from typing import Optional
from fastapi import Depends, HTTPException, Header, Query
from fastapi.security import APIKeyHeader

from app.core import settings, logger
from app.core.exceptions import AuthenticationException
from app.models.schemas import PaginationParams
from app.services.database import mongo_repository


# Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    Verifica la API key
    
    Args:
        api_key: API key del header
        
    Returns:
        API key validada
        
    Raises:
        HTTPException: Si la API key es inválida
    """
    if not api_key:
        logger.warning("Intento de acceso sin API key")
        raise HTTPException(
            status_code=401,
            detail="API key requerida",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key != settings.api_key:
        logger.warning("Intento de acceso con API key inválida", api_key=api_key[:8] + "...")
        raise HTTPException(
            status_code=401,
            detail="API key inválida",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key


async def get_pagination_params(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página")
) -> PaginationParams:
    """
    Obtiene parámetros de paginación
    
    Args:
        page: Número de página
        page_size: Tamaño de página
        
    Returns:
        PaginationParams con los valores validados
    """
    return PaginationParams(page=page, page_size=page_size)


async def get_db():
    """
    Dependencia para obtener la conexión a la base de datos
    
    Yields:
        MongoRepository conectado
    """
    try:
        await mongo_repository.connect()
        yield mongo_repository
    except Exception as e:
        logger.error("Error conectando a la base de datos", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Base de datos no disponible"
        )


# Dependencias opcionales para desarrollo
async def optional_api_key(api_key: Optional[str] = Depends(api_key_header)) -> Optional[str]:
    """
    Verifica la API key solo si está presente
    Útil para endpoints que pueden ser públicos en desarrollo
    """
    if settings.is_development:
        # En desarrollo, la API key es opcional
        return api_key
    
    # En producción, siempre requerida
    return await verify_api_key(api_key)


# Headers comunes
async def get_request_id(x_request_id: Optional[str] = Header(None)) -> Optional[str]:
    """Obtiene el ID de request para trazabilidad"""
    return x_request_id


# Validaciones de parámetros
def validate_database_name(database: str) -> str:
    """Valida el nombre de la base de datos"""
    if not database or not database.strip():
        raise HTTPException(
            status_code=400,
            detail="El nombre de la base de datos no puede estar vacío"
        )
    return database.strip()


def validate_collection_name(collection: str) -> str:
    """Valida el nombre de la colección"""
    if not collection or not collection.strip():
        raise HTTPException(
            status_code=400,
            detail="El nombre de la colección no puede estar vacío"
        )
    return collection.strip()


def validate_document_id(document_id: str) -> str:
    """Valida el ID del documento"""
    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=400,
            detail="El ID del documento no puede estar vacío"
        )
    
    # Validar que es un ObjectId válido
    from bson import ObjectId
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=400,
            detail="El ID del documento no es válido"
        )
    
    return document_id.strip()
