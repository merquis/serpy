"""
Repositorio MongoDB - Gestión de operaciones de base de datos
"""
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class MongoRepository:
    """Repositorio para operaciones con MongoDB"""
    
    def __init__(self, uri: str, db_name: str):
        """
        Inicializa el repositorio de MongoDB
        
        Args:
            uri: URI de conexión a MongoDB
            db_name: Nombre de la base de datos
        """
        self.client: MongoClient = None
        self.db: Database = None
        self.uri = uri
        self.db_name = db_name
        self._connect()
    
    def _connect(self):
        """Establece la conexión con MongoDB"""
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            # Verificar conexión
            self.client.admin.command('ping')
            logger.info(f"Conectado a MongoDB: {self.db_name}")
        except Exception as e:
            logger.error(f"Error conectando a MongoDB: {e}")
            raise
    
    def get_collection(self, collection_name: str) -> Collection:
        """Obtiene una colección"""
        return self.db[collection_name]
    
    def insert_one(
        self, 
        document: Dict[str, Any],
        collection_name: str
    ) -> str:
        """
        Inserta un documento en la colección
        
        Args:
            document: Documento a insertar
            collection_name: Nombre de la colección
            
        Returns:
            ID del documento insertado
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.insert_one(document)
            logger.info(f"Documento insertado en {collection_name}: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error insertando documento en {collection_name}: {e}")
            logger.error(f"Documento que se intentó insertar: {document}")
            raise
    
    def insert_many(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str
    ) -> List[str]:
        """
        Inserta múltiples documentos en la colección
        
        Args:
            documents: Lista de documentos a insertar
            collection_name: Nombre de la colección
            
        Returns:
            Lista de IDs de documentos insertados
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.insert_many(documents)
            logger.info(f"{len(result.inserted_ids)} documentos insertados en {collection_name}")
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Error insertando documentos: {e}")
            raise
    
    def find_one(
        self,
        filter_dict: Dict[str, Any],
        collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Busca un documento en la colección
        
        Args:
            filter_dict: Filtro de búsqueda
            collection_name: Nombre de la colección
            
        Returns:
            Documento encontrado o None
        """
        try:
            # Convertir _id string a ObjectId si es necesario
            if "_id" in filter_dict and isinstance(filter_dict["_id"], str):
                try:
                    filter_dict["_id"] = ObjectId(filter_dict["_id"])
                except:
                    pass  # Si falla, dejar como string
            
            collection = self.get_collection(collection_name)
            document = collection.find_one(filter_dict)
            if document and "_id" in document:
                document["_id"] = str(document["_id"])
            return document
        except Exception as e:
            logger.error(f"Error buscando documento: {e}")
            return None
    
    def find_many(
        self,
        filter_dict: Dict[str, Any],
        collection_name: str,
        limit: int = 0,
        skip: int = 0,
        sort: List[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca múltiples documentos en la colección
        
        Args:
            filter_dict: Filtro de búsqueda
            collection_name: Nombre de la colección
            limit: Límite de resultados (0 = sin límite)
            skip: Número de documentos a saltar
            sort: Lista de tuplas (campo, dirección) para ordenar
            
        Returns:
            Lista de documentos encontrados
        """
        try:
            collection = self.get_collection(collection_name)
            cursor = collection.find(filter_dict)
            
            if skip > 0:
                cursor = cursor.skip(skip)
            if limit > 0:
                cursor = cursor.limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            
            documents = []
            for doc in cursor:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error(f"Error buscando documentos: {e}")
            return []
    
    def update_one(
        self,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any],
        collection_name: str,
        upsert: bool = False
    ) -> bool:
        """
        Actualiza un documento en la colección
        
        Args:
            filter_dict: Filtro para encontrar el documento
            update_dict: Datos a actualizar
            collection_name: Nombre de la colección
            upsert: Si crear el documento si no existe
            
        Returns:
            True si se actualizó, False si no
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.update_one(
                filter_dict,
                {"$set": update_dict},
                upsert=upsert
            )
            updated = result.modified_count > 0 or result.upserted_id is not None
            logger.info(f"Documento {'actualizado' if updated else 'no actualizado'} en {collection_name}")
            return updated
        except Exception as e:
            logger.error(f"Error actualizando documento: {e}")
            return False
    
    def delete_one(
        self,
        filter_dict: Dict[str, Any],
        collection_name: str
    ) -> bool:
        """
        Elimina un documento de la colección
        
        Args:
            filter_dict: Filtro para encontrar el documento
            collection_name: Nombre de la colección
            
        Returns:
            True si se eliminó, False si no
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.delete_one(filter_dict)
            deleted = result.deleted_count > 0
            logger.info(f"Documento {'eliminado' if deleted else 'no encontrado'} en {collection_name}")
            return deleted
        except Exception as e:
            logger.error(f"Error eliminando documento: {e}")
            return False
    
    def count_documents(
        self,
        filter_dict: Dict[str, Any],
        collection_name: str
    ) -> int:
        """
        Cuenta documentos en la colección
        
        Args:
            filter_dict: Filtro de búsqueda
            collection_name: Nombre de la colección
            
        Returns:
            Número de documentos
        """
        try:
            collection = self.get_collection(collection_name)
            return collection.count_documents(filter_dict)
        except Exception as e:
            logger.error(f"Error contando documentos: {e}")
            return 0
    
    def create_index(
        self,
        keys: List[tuple],
        collection_name: str,
        unique: bool = False,
        name: Optional[str] = None
    ) -> str:
        """
        Crea un índice en la colección
        
        Args:
            keys: Lista de tuplas (campo, dirección)
            collection_name: Nombre de la colección
            unique: Si el índice debe ser único
            name: Nombre del índice
            
        Returns:
            Nombre del índice creado
        """
        try:
            collection = self.get_collection(collection_name)
            index_name = collection.create_index(
                keys,
                unique=unique,
                name=name
            )
            logger.info(f"Índice creado en {collection_name}: {index_name}")
            return index_name
        except Exception as e:
            logger.error(f"Error creando índice: {e}")
            raise
    
    def close(self):
        """Cierra la conexión con MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Conexión con MongoDB cerrada")
