"""
API principal de SERPY
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse
from pymongo import MongoClient
from bson import ObjectId
from typing import Optional, List, Dict, Any
import logging
import json

from config.settings import config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title=config.app.app_name,
    description=config.app.app_description,
    version=config.app.app_version,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.cors_origins,
    allow_credentials=config.security.cors_credentials,
    allow_methods=config.security.cors_methods,
    allow_headers=config.security.cors_headers,
)

# Cliente MongoDB
mongo_client: Optional[MongoClient] = None
db = None
available_collections_cache: List[str] = []


def get_available_collections() -> List[str]:
    """Obtiene las colecciones disponibles de MongoDB"""
    global available_collections_cache
    
    # Lista predefinida de colecciones conocidas
    KNOWN_COLLECTIONS = [
        "posts",
        "hoteles", 
        "URLs Google",
        "URLs Google Tags"
    ]
    
    if not available_collections_cache:
        try:
            db = get_mongo_client()
            if db:
                # Obtener todas las colecciones de MongoDB
                all_collections = db.list_collection_names()
                # Filtrar colecciones del sistema
                available_collections_cache = [
                    col for col in all_collections 
                    if not col.startswith('system.')
                ]
                logger.info(f"Colecciones disponibles desde MongoDB: {available_collections_cache}")
            else:
                # Si no hay conexión, usar las colecciones conocidas
                logger.warning("No hay conexión a MongoDB, usando colecciones predefinidas")
                available_collections_cache = KNOWN_COLLECTIONS
        except Exception as e:
            logger.error(f"Error obteniendo colecciones: {e}")
            # En caso de error, usar las colecciones conocidas
            available_collections_cache = KNOWN_COLLECTIONS
            logger.info(f"Usando colecciones predefinidas: {available_collections_cache}")
    
    return available_collections_cache


def pretty_json_response(data: Any) -> PlainTextResponse:
    """Devuelve una respuesta JSON formateada con indentación"""
    # Convertir a JSON string con formato bonito
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    # Devolver como texto plano para que el navegador muestre el formato
    return PlainTextResponse(
        content=json_str,
        media_type="application/json; charset=utf-8"
    )


def get_mongo_client():
    """Obtiene el cliente de MongoDB"""
    global mongo_client, db
    if mongo_client is None:
        try:
            mongo_client = MongoClient(
                config.mongo_uri,
                serverSelectionTimeoutMS=5000,  # Timeout más corto para fallar rápido
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            db = mongo_client[config.app.mongo_default_db]
            # Verificar conexión
            mongo_client.admin.command('ping')
            logger.info(f"Conectado a MongoDB: {config.app.mongo_default_db}")
        except Exception as e:
            logger.error(f"Error conectando a MongoDB: {e}")
            # No lanzar excepción aquí para que la API pueda iniciar
            db = None
    return db


@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    logger.info(f"Iniciando {config.app.app_name} en modo {config.environment}")
    logger.info(f"API Base URL: {config.app.api_base_url}")
    logger.info(f"Intentando conectar a MongoDB...")
    
    # Intentar conectar pero no fallar si no se puede
    try:
        get_mongo_client()
        # Cargar colecciones disponibles
        get_available_collections()
    except Exception as e:
        logger.warning(f"No se pudo conectar a MongoDB al inicio: {e}")
        logger.warning("La API continuará funcionando pero las operaciones de base de datos fallarán")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicación"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("Conexión con MongoDB cerrada")


@app.get("/")
async def root():
    """Endpoint raíz - redirige a la documentación"""
    if config.debug:
        return RedirectResponse(url="/docs")
    
    collections = get_available_collections()
    # Crear mapeo de slugs
    collection_slugs = {
        config.app.collection_to_slug(col): col 
        for col in collections
    }
    
    return pretty_json_response({
        "name": config.app.app_name,
        "version": config.app.app_version,
        "collections": collections,
        "collection_slugs": collection_slugs
    })


@app.get("/health")
async def health_check():
    """Verificación de salud de la API"""
    health_status = {
        "status": "healthy",
        "service": config.app.app_name,
        "version": config.app.app_version,
        "environment": config.environment,
        "api_base_url": config.app.api_base_url
    }
    
    # Verificar conexión a MongoDB
    try:
        db = get_mongo_client()
        if db is not None:
            db.command('ping')
            health_status["database"] = "connected"
            health_status["database_name"] = config.app.mongo_default_db
        else:
            health_status["status"] = "degraded"
            health_status["database"] = "disconnected"
            health_status["database_error"] = "No se pudo establecer conexión"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = "disconnected"
        health_status["database_error"] = str(e)
    
    return pretty_json_response(health_status)


@app.get("/collections")
async def list_collections():
    """Lista las colecciones disponibles"""
    try:
        db = get_mongo_client()
        if db is None:
            raise HTTPException(
                status_code=503, 
                detail="Base de datos no disponible. Por favor, verifica la conexión a MongoDB."
            )
        
        collections = get_available_collections()
        
        # Crear información de colecciones con sus slugs
        collection_info = []
        for col in collections:
            slug = config.app.collection_to_slug(col)
            collection_info.append({
                "name": col,
                "slug": slug,
                "url": f"{config.app.api_base_url}/{slug}"
            })
        
        return pretty_json_response({
            "collections": collection_info,
            "total": len(collections)
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando colecciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/{collection_slug}")
async def list_documents(
    collection_slug: str,
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(config.app.default_page_size, ge=1, le=config.app.max_page_size, description="Tamaño de página"),
    search: Optional[str] = Query(None, description="Búsqueda en título o contenido")
):
    """Lista documentos de una colección con paginación"""
    # Convertir slug a nombre real de colección
    available_collections = get_available_collections()
    collection = config.app.slug_to_collection(collection_slug, available_collections)
    
    if not collection:
        raise HTTPException(status_code=404, detail=f"Colección '{collection_slug}' no disponible")
    
    try:
        db = get_mongo_client()
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Base de datos no disponible. Por favor, verifica la conexión a MongoDB."
            )
        col = db[collection]
        
        # Construir filtro de búsqueda
        filter_dict = {}
        if search:
            filter_dict["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"content": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}}
            ]
        
        # Calcular paginación
        skip = (page - 1) * page_size
        
        # Obtener documentos
        cursor = col.find(filter_dict).skip(skip).limit(page_size)
        documents = []
        
        for doc in cursor:
            # Convertir ObjectId a string
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            # Añadir URL de detalle usando el slug de la colección
            if "slug" in doc and doc["slug"]:
                doc["detail_url"] = f"{config.app.api_base_url}/{collection_slug}/{doc['_id']}-{doc['slug']}"
            else:
                doc["detail_url"] = f"{config.app.api_base_url}/{collection_slug}/{doc['_id']}"
            documents.append(doc)
        
        # Contar total de documentos
        total = col.count_documents(filter_dict)
        total_pages = (total + page_size - 1) // page_size
        
        return pretty_json_response({
            "collection": collection,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "documents": documents
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo documentos de {collection}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/{collection_slug}/{document_id}")
async def get_document(collection_slug: str, document_id: str):
    """Obtiene un documento específico por ID (con o sin slug)"""
    # Convertir slug a nombre real de colección
    available_collections = get_available_collections()
    collection = config.app.slug_to_collection(collection_slug, available_collections)
    
    if not collection:
        raise HTTPException(status_code=404, detail=f"Colección '{collection_slug}' no disponible")
    
    try:
        # Extraer el ID real (puede venir como "id-slug" o solo "id")
        actual_id = document_id.split('-')[0] if '-' in document_id else document_id
        
        # Validar que es un ObjectId válido
        if not ObjectId.is_valid(actual_id):
            raise HTTPException(status_code=400, detail="ID de documento inválido")
        
        db = get_mongo_client()
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Base de datos no disponible. Por favor, verifica la conexión a MongoDB."
            )
        col = db[collection]
        
        # Buscar documento
        document = col.find_one({"_id": ObjectId(actual_id)})
        
        if not document:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Convertir ObjectId a string
        document["_id"] = str(document["_id"])
        
        # Añadir información adicional
        document["collection"] = collection
        if "slug" in document and document["slug"]:
            document["canonical_url"] = f"{config.app.api_base_url}/{collection_slug}/{document['_id']}-{document['slug']}"
        else:
            document["canonical_url"] = f"{config.app.api_base_url}/{collection_slug}/{document['_id']}"
        
        return pretty_json_response(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo documento {document_id} de {collection}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/{collection_slug}/search/{query}")
async def search_in_collection(
    collection_slug: str,
    query: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(config.app.default_page_size, ge=1, le=config.app.max_page_size)
):
    """Busca documentos en una colección específica"""
    # Convertir slug a nombre real de colección
    available_collections = get_available_collections()
    collection = config.app.slug_to_collection(collection_slug, available_collections)
    
    if not collection:
        raise HTTPException(status_code=404, detail=f"Colección '{collection_slug}' no disponible")
    
    try:
        db = get_mongo_client()
        if db is None:
            raise HTTPException(
                status_code=503,
                detail="Base de datos no disponible. Por favor, verifica la conexión a MongoDB."
            )
        col = db[collection]
        
        # Construir filtro de búsqueda
        filter_dict = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"content": {"$regex": query, "$options": "i"}},
                {"name": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}}
            ]
        }
        
        # Calcular paginación
        skip = (page - 1) * page_size
        
        # Obtener documentos
        cursor = col.find(filter_dict).skip(skip).limit(page_size)
        documents = []
        
        for doc in cursor:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            if "slug" in doc and doc["slug"]:
                doc["detail_url"] = f"{config.app.api_base_url}/{collection_slug}/{doc['_id']}-{doc['slug']}"
            else:
                doc["detail_url"] = f"{config.app.api_base_url}/{collection_slug}/{doc['_id']}"
            documents.append(doc)
        
        # Contar total
        total = col.count_documents(filter_dict)
        total_pages = (total + page_size - 1) // page_size
        
        return pretty_json_response({
            "collection": collection,
            "query": query,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "documents": documents
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error buscando en {collection}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.app.api_host,
        port=config.app.api_port,
        reload=config.debug
    )
