from pymongo import MongoClient
from collections.abc import MutableMapping
from typing import List, Dict, Any, Optional, Union

# URI por defecto para MongoDB
DEFAULT_URI = "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"

# ─────────────────────────────────────────────────────────────────────
# CREAR / INSERTAR
# ─────────────────────────────────────────────────────────────────────

def subir_a_mongodb(
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    db_name: str,
    collection_name: str,
    uri: str = DEFAULT_URI
) -> Union[str, List[str]]:
    """
    Inserta uno o varios documentos en MongoDB.
    - Si 'data' es un dict, usa insert_one.
    - Si 'data' es una lista de dicts, usa insert_many.
    Devuelve el ID o los IDs insertados (como strings).
    """
    client = MongoClient(uri)
    collection = client[db_name][collection_name]

    if isinstance(data, list):
        if not all(isinstance(d, dict) for d in data):
            raise ValueError("Todos los elementos deben ser diccionarios.")
        result = collection.insert_many(data, ordered=False)
        return [str(_id) for _id in result.inserted_ids]

    elif isinstance(data, MutableMapping):
        result = collection.insert_one(data)
        return str(result.inserted_id)

    else:
        raise ValueError("Debes pasar un dict o una lista de dicts.")


# ─────────────────────────────────────────────────────────────────────
# OBTENER LISTA DE DOCUMENTOS (Nombres)
# ─────────────────────────────────────────────────────────────────────

def obtener_documentos_mongodb(
    uri: str,
    db_name: str,
    collection_name: str,
    filtro: Optional[Dict[str, Any]] = None,
    campo_nombre: str = "busqueda"
) -> List[str]:
    """
    Devuelve una lista con los valores únicos del campo 'campo_nombre'
    de todos los documentos que cumplan 'filtro'.
    """
    client = MongoClient(uri)
    collection = client[db_name][collection_name]
    cursor = collection.find(filtro or {}, {campo_nombre: 1, "_id": 0})
    return [doc[campo_nombre] for doc in cursor if campo_nombre in doc]


# ─────────────────────────────────────────────────────────────────────
# OBTENER UN DOCUMENTO COMPLETO POR CLAVE
# ─────────────────────────────────────────────────────────────────────

def obtener_documento_mongodb(
    uri: str,
    db_name: str,
    collection_name: str,
    valor_busqueda: str,
    campo_nombre: str = "busqueda"
) -> Optional[Dict[str, Any]]:
    """
    Recupera un documento cuyo campo 'campo_nombre' coincida con 'valor_busqueda'.
    Excluye el campo '_id' del resultado.
    """
    client = MongoClient(uri)
    collection = client[db_name][collection_name]
    return collection.find_one({campo_nombre: valor_busqueda}, {"_id": 0})
