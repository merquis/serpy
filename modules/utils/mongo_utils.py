from pymongo import MongoClient
from typing import List, Dict, Any, Optional

DEFAULT_URI = "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"

# ---------- CREAR / INSERTAR ----------
def subir_a_mongodb(
    data: Dict[str, Any],
    db_name: str,
    collection_name: str,
    uri: str = DEFAULT_URI
):
    """Inserta un documento (data) y devuelve su ObjectId."""
    client = MongoClient(uri)
    collection = client[db_name][collection_name]
    result = collection.insert_one(data)
    return result.inserted_id


# ---------- LEER LISTA DE DOCUMENTOS ----------
def obtener_documentos_mongodb(
    uri: str,
    db_name: str,
    collection_name: str,
    filtro: Optional[Dict[str, Any]] = None,
    campo_nombre: str = "busqueda"
) -> List[str]:
    """
    Devuelve una lista con los valores únicos de 'campo_nombre'
    de todos los documentos que cumplan 'filtro'.
    """
    client = MongoClient(uri)
    collection = client[db_name][collection_name]
    cursor = collection.find(filtro or {}, {campo_nombre: 1, "_id": 0})
    return [doc[campo_nombre] for doc in cursor if campo_nombre in doc]


# ---------- LEER DOCUMENTO COMPLETO ----------
def obtener_documento_mongodb(
    uri: str,
    db_name: str,
    collection_name: str,
    valor_busqueda: str,
    campo_nombre: str = "busqueda"
) -> Optional[Dict[str, Any]]:
    """
    Recupera un documento completo cuyo campo 'campo_nombre'
    coincida exactamente con 'valor_busqueda' (excluye _id).
    """
    client = MongoClient(uri)
    collection = client[db_name][collection_name]
    return collection.find_one({campo_nombre: valor_busqueda}, {"_id": 0})
