"""
Repositorio base para operaciones de datos
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from contextlib import contextmanager
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from config import config
import logging

logger = logging.getLogger(__name__)

class BaseRepository(ABC):
    """Clase base abstracta para repositorios"""
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> str:
        """Crear un nuevo registro"""
        pass
    
    @abstractmethod
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Buscar un registro"""
        pass
    
    @abstractmethod
    def find_many(self, query: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar múltiples registros"""
        pass
    
    @abstractmethod
    def update(self, query: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Actualizar un registro"""
        pass
    
    @abstractmethod
    def delete(self, query: Dict[str, Any]) -> bool:
        """Eliminar un registro"""
        pass

class MongoRepository(BaseRepository):
    """Implementación de repositorio para MongoDB"""
    
    def __init__(
        self, 
        db_name: str = None, 
        collection_name: str = None,
        uri: str = None
    ):
        self.uri = uri or config.mongo_uri
        self.db_name = db_name or config.app.mongo_default_db
        self.collection_name = collection_name or config.app.mongo_default_collection
        self._client = None
    
    @contextmanager
    def get_collection(self) -> Collection:
        """Context manager para obtener la colección de MongoDB"""
        try:
            if not self._client:
                self._client = MongoClient(self.uri)
            
            collection = self._client[self.db_name][self.collection_name]
            yield collection
        except PyMongoError as e:
            logger.error(f"Error de MongoDB: {e}")
            raise
        finally:
            # No cerramos la conexión aquí para reutilizarla
            pass
    
    def close(self):
        """Cerrar la conexión a MongoDB"""
        if self._client:
            self._client.close()
            self._client = None
    
    def create(self, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[str, List[str]]:
        """
        Crear uno o varios documentos
        Returns: ID(s) del documento(s) creado(s)
        """
        with self.get_collection() as collection:
            if isinstance(data, list):
                if not all(isinstance(d, dict) for d in data):
                    raise ValueError("Todos los elementos deben ser diccionarios")
                result = collection.insert_many(data, ordered=False)
                return [str(id_) for id_ in result.inserted_ids]
            else:
                result = collection.insert_one(data)
                return str(result.inserted_id)
    
    def find_one(
        self, 
        query: Dict[str, Any], 
        projection: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Buscar un documento"""
        with self.get_collection() as collection:
            if projection is None:
                projection = {"_id": 0}
            return collection.find_one(query, projection)
    
    def find_many(
        self, 
        query: Dict[str, Any] = None,
        projection: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """Buscar múltiples documentos con opciones de paginación y ordenamiento"""
        with self.get_collection() as collection:
            if projection is None:
                projection = {"_id": 0}
            
            cursor = collection.find(query or {}, projection)
            
            if skip > 0:
                cursor = cursor.skip(skip)
            
            if limit > 0:
                cursor = cursor.limit(limit)
            
            if sort:
                cursor = cursor.sort(sort)
            
            return list(cursor)
    
    def update(
        self, 
        query: Dict[str, Any], 
        data: Dict[str, Any],
        upsert: bool = False,
        update_many: bool = False
    ) -> int:
        """
        Actualizar documento(s)
        Returns: Número de documentos modificados
        """
        with self.get_collection() as collection:
            # Asegurar que los datos de actualización tienen el operador correcto
            if not any(key.startswith('$') for key in data.keys()):
                data = {"$set": data}
            
            if update_many:
                result = collection.update_many(query, data, upsert=upsert)
            else:
                result = collection.update_one(query, data, upsert=upsert)
            
            return result.modified_count
    
    def delete(self, query: Dict[str, Any], delete_many: bool = False) -> int:
        """
        Eliminar documento(s)
        Returns: Número de documentos eliminados
        """
        with self.get_collection() as collection:
            if delete_many:
                result = collection.delete_many(query)
            else:
                result = collection.delete_one(query)
            
            return result.deleted_count
    
    def count(self, query: Dict[str, Any] = None) -> int:
        """Contar documentos que coinciden con la consulta"""
        with self.get_collection() as collection:
            return collection.count_documents(query or {})
    
    def distinct(self, field: str, query: Dict[str, Any] = None) -> List[Any]:
        """Obtener valores únicos de un campo"""
        with self.get_collection() as collection:
            return collection.distinct(field, query or {})
    
    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ejecutar una pipeline de agregación"""
        with self.get_collection() as collection:
            return list(collection.aggregate(pipeline))
    
    def __enter__(self):
        """Soporte para context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cerrar conexión al salir del context manager"""
        self.close() 