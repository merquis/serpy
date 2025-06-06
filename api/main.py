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
    """Obtiene las colecciones disponibles de MongoDB dinámicamente"""
    global available_collections_cache
    
    if not available_collections_cache:
        try:
            db = get_mongo_client()
            if db is not None:
                # Obtener todas las colecciones de MongoDB
                all_collections = db.list_collection_names()
                # Filtrar colecciones del sistema
                available_collections_cache = [
                    col for col in all_collections 
                    if not col.startswith('system.')
                ]
                logger.info(f"Colecciones disponibles desde MongoDB: {available_collections_cache}")
            else:
                logger.error("No hay conexión a MongoDB, no se pueden obtener colecciones")
                available_collections_cache = []
        except Exception as e:
            logger.error(f"Error obteniendo colecciones: {type(e).__name__}: {e}")
            available_collections_cache = []
    
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
            logger.info(f"Intentando conectar a MongoDB con URI: {config.mongo_uri.split('@')[0]}@...")
            mongo_client = MongoClient(
                config.mongo_uri,
                serverSelectionTimeoutMS=5000,  # Timeout más corto para fallar rápido
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            # Primero verificar la conexión
            mongo_client.admin.command('ping')
            logger.info("Conexión a MongoDB establecida correctamente")
            
            # Luego obtener la base de datos
            db = mongo_client[config.app.mongo_default_db]
            logger.info(f"Base de datos seleccionada: {config.app.mongo_default_db}")
            
            # Verificar que podemos listar colecciones
            test_collections = db.list_collection_names()
            logger.info(f"Prueba de listado de colecciones exitosa. Encontradas: {len(test_collections)} colecciones")
            
        except Exception as e:
            logger.error(f"Error conectando a MongoDB: {type(e).__name__}: {e}")
            # No lanzar excepción aquí para que la API pueda iniciar
            db = None
            mongo_client = None
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
    """Endpoint raíz - muestra información de la API y enlaces a todas las colecciones"""
    collections = get_available_collections()
    
    # Crear información detallada de cada colección con sus URLs
    collections_info = []
    for col in collections:
        slug = config.app.collection_to_slug(col)
        collections_info.append({
            "name": col,
            "slug": slug,
            "endpoints": {
                "list": f"{config.app.api_base_url}/{slug}",
                "search": f"{config.app.api_base_url}/{slug}/search/{{query}}",
                "detail": f"{config.app.api_base_url}/{slug}/{{document_id}}"
            }
        })
    
    # URLs principales de la API
    api_info = {
        "name": config.app.app_name,
        "version": config.app.app_version,
        "description": config.app.app_description,
        "base_url": config.app.api_base_url,
        "endpoints": {
            "health": f"{config.app.api_base_url}/health",
            "collections": f"{config.app.api_base_url}/collections",
            "reload_collections": f"{config.app.api_base_url}/reload-collections"
        },
        "collections": collections_info,
        "usage_examples": {
            "list_posts": f"{config.app.api_base_url}/posts",
            "search_posts": f"{config.app.api_base_url}/posts/search/lanzarote",
            "get_post": f"{config.app.api_base_url}/posts/68407473fc91e2815c748b71-slug-opcional",
            "pagination": f"{config.app.api_base_url}/posts?page=2&page_size=10",
            "list_hotels": f"{config.app.api_base_url}/hotel-booking",
            "search_hotels": f"{config.app.api_base_url}/hotel-booking/search/tenerife",
            "get_hotel": f"{config.app.api_base_url}/hotel-booking/6840bc4e949575a0325d921b-vincci-seleccion-la-plantacion-del-sur"
        },
        "features": {
            "pagination": "Todos los endpoints de listado soportan paginación con parámetros 'page' y 'page_size'",
            "search": "Búsqueda de texto completo en título, contenido, nombre y descripción",
            "slug_support": "Los IDs de documentos pueden incluir un slug opcional para URLs más amigables",
            "json_formatting": "Respuestas JSON formateadas con indentación para mejor legibilidad"
        },
        "related_services": {
            "images_service": {
                "url": "https://images.serpsrewrite.com",
                "description": "Servicio de gestión y descarga de imágenes para las colecciones",
                "features": {
                    "download_images": "Descarga automática de imágenes desde documentos MongoDB",
                    "serve_images": "Sirve imágenes con URLs directas y estructura organizada",
                    "directory_structure": "/images/[database]/[collection]/[mongo_id]-[name]/original/",
                    "api_integration": "Integración completa con esta API para descargar imágenes de cualquier documento"
                },
                "example_usage": {
                    "download_endpoint": "POST https://images.serpsrewrite.com/api/v1/download/from-api-url-simple",
                    "download_body": {
                        "api_url": "https://api.serpsrewrite.com/hotel-booking/[document_id]",
                        "database_name": "serpy_db",
                        "collection_name": "hotel-booking"
                    },
                    "serve_image": "https://images.serpsrewrite.com/api/v1/images/serpy_db/hotel-booking/[id]-[name]/original/img_001.jpg"
                }
            }
        },
        "integration_with_images": {
            "description": "Esta API está completamente integrada con el servicio de imágenes",
            "workflow": [
                "1. Obtén un documento de cualquier colección usando esta API",
                "2. Usa el ID del documento para descargar sus imágenes con el servicio de imágenes",
                "3. Las imágenes se organizarán automáticamente por database/collection/document",
                "4. Accede a las imágenes con URLs directas desde images.serpsrewrite.com"
            ],
            "supported_collections": [
                "hotel-booking: Hoteles de Booking.com con imágenes",
                "posts: Artículos del blog con imágenes destacadas",
                "Y cualquier otra colección que contenga campos de imágenes"
            ]
        }
    }
    
    if config.debug:
        api_info["documentation"] = {
            "swagger": f"{config.app.api_base_url}/docs",
            "redoc": f"{config.app.api_base_url}/redoc"
        }
    
    return pretty_json_response(api_info)


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
            # Intentar listar colecciones para más información
            try:
                cols = db.list_collection_names()
                health_status["collections_count"] = len(cols)
                health_status["collections_sample"] = cols[:5] if cols else []
            except Exception as e:
                health_status["collections_error"] = str(e)
        else:
            health_status["status"] = "degraded"
            health_status["database"] = "disconnected"
            health_status["database_error"] = "No se pudo establecer conexión"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = "disconnected"
        health_status["database_error"] = str(e)
    
    return pretty_json_response(health_status)


@app.get("/debug/mongodb")
async def debug_mongodb():
    """Endpoint de debug para diagnosticar problemas con MongoDB"""
    debug_info = {
        "mongo_uri": config.mongo_uri.split('@')[0] + "@...",  # Ocultar credenciales
        "database_name": config.app.mongo_default_db,
        "connection_test": {}
    }
    
    # Resetear la conexión para forzar un nuevo intento
    global mongo_client, db, available_collections_cache
    if mongo_client:
        try:
            mongo_client.close()
        except:
            pass
    mongo_client = None
    db = None
    available_collections_cache = []
    
    # Intentar conectar con más detalle
    try:
        debug_info["connection_test"]["step"] = "Creating MongoClient"
        test_client = MongoClient(
            config.mongo_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000
        )
        
        debug_info["connection_test"]["step"] = "Ping admin database"
        test_client.admin.command('ping')
        debug_info["connection_test"]["ping"] = "success"
        
        debug_info["connection_test"]["step"] = "Get database"
        test_db = test_client[config.app.mongo_default_db]
        
        debug_info["connection_test"]["step"] = "List collection names"
        collections = test_db.list_collection_names()
        debug_info["connection_test"]["collections"] = collections
        debug_info["connection_test"]["collections_count"] = len(collections)
        
        debug_info["connection_test"]["step"] = "Test complete"
        debug_info["connection_test"]["status"] = "success"
        
        test_client.close()
        
    except Exception as e:
        debug_info["connection_test"]["error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "step": debug_info["connection_test"].get("step", "unknown")
        }
        debug_info["connection_test"]["status"] = "failed"
    
    return pretty_json_response(debug_info)


@app.get("/reload-collections")
async def reload_collections():
    """Fuerza la recarga de las colecciones desde MongoDB"""
    global available_collections_cache
    
    # Limpiar caché
    available_collections_cache = []
    
    # Intentar obtener las colecciones nuevamente
    try:
        db = get_mongo_client()
        if db is not None:
            # Método 1: list_collection_names()
            try:
                collections_method1 = db.list_collection_names()
                logger.info(f"Método 1 - list_collection_names(): {collections_method1}")
            except Exception as e:
                collections_method1 = f"Error: {e}"
            
            # Método 2: list_collections()
            try:
                collections_method2 = [col["name"] for col in db.list_collections()]
                logger.info(f"Método 2 - list_collections(): {collections_method2}")
            except Exception as e:
                collections_method2 = f"Error: {e}"
            
            # Método 3: Acceso directo a collection_names (deprecated pero puede funcionar)
            try:
                if hasattr(db, 'collection_names'):
                    collections_method3 = db.collection_names()
                    logger.info(f"Método 3 - collection_names(): {collections_method3}")
                else:
                    collections_method3 = "Método no disponible"
            except Exception as e:
                collections_method3 = f"Error: {e}"
            
            # Usar el método que funcione
            if isinstance(collections_method1, list):
                available_collections_cache = [
                    col for col in collections_method1 
                    if not col.startswith('system.')
                ]
            elif isinstance(collections_method2, list):
                available_collections_cache = [
                    col for col in collections_method2 
                    if not col.startswith('system.')
                ]
            
            return pretty_json_response({
                "status": "success",
                "collections_found": available_collections_cache,
                "methods_tried": {
                    "list_collection_names": collections_method1,
                    "list_collections": collections_method2,
                    "collection_names": collections_method3
                },
                "cache_updated": True
            })
        else:
            return pretty_json_response({
                "status": "error",
                "message": "No hay conexión a MongoDB",
                "cache_updated": False
            })
    except Exception as e:
        logger.error(f"Error recargando colecciones: {e}")
        return pretty_json_response({
            "status": "error",
            "message": str(e),
            "cache_updated": False
        })


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
