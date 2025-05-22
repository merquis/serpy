"""
Servicio de Google Drive - Gestión mejorada de archivos y carpetas
"""
from typing import Dict, List, Optional, Union, BinaryIO, Any
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import json
import logging
from config import config

logger = logging.getLogger(__name__)

class DriveService:
    """Servicio mejorado para interactuar con Google Drive"""
    
    def __init__(self):
        self.drive = self._initialize_drive()
        self._file_cache = {}
        
    def _initialize_drive(self) -> GoogleDrive:
        """Inicializa la conexión con Google Drive usando credenciales de servicio"""
        try:
            gauth = GoogleAuth()
            gauth.auth_method = 'service'
            gauth.credentials = service_account.Credentials.from_service_account_info(
                config.drive_credentials,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            return GoogleDrive(gauth)
        except Exception as e:
            logger.error(f"Error inicializando Google Drive: {e}")
            raise
    
    def list_files(
        self, 
        folder_id: str, 
        file_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, str]:
        """
        Lista archivos en una carpeta
        
        Args:
            folder_id: ID de la carpeta
            file_type: Filtrar por tipo MIME (ej: 'application/json')
            limit: Número máximo de archivos a retornar
            
        Returns:
            Diccionario {nombre_archivo: id_archivo}
        """
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            if file_type:
                query += f" and mimeType='{file_type}'"
                
            file_list = self.drive.ListFile({
                'q': query,
                'maxResults': limit
            }).GetList()
            
            return {file['title']: file['id'] for file in file_list}
        except Exception as e:
            logger.error(f"Error listando archivos: {e}")
            return {}
    
    def create_folder(
        self, 
        folder_name: str, 
        parent_folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Crea una nueva carpeta
        
        Args:
            folder_name: Nombre de la carpeta
            parent_folder_id: ID de la carpeta padre
            
        Returns:
            ID de la carpeta creada o None si falla
        """
        try:
            folder_metadata = {
                'title': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [{'id': parent_folder_id}]
            
            folder = self.drive.CreateFile(folder_metadata)
            folder.Upload()
            
            logger.info(f"Carpeta '{folder_name}' creada con ID: {folder['id']}")
            return folder['id']
        except Exception as e:
            logger.error(f"Error creando carpeta: {e}")
            return None
    
    def get_or_create_folder(
        self, 
        folder_name: str, 
        parent_folder_id: str
    ) -> str:
        """
        Obtiene el ID de una carpeta o la crea si no existe
        
        Args:
            folder_name: Nombre de la carpeta
            parent_folder_id: ID de la carpeta padre
            
        Returns:
            ID de la carpeta
        """
        # Buscar si la carpeta ya existe
        existing_folders = self.list_folders(parent_folder_id)
        
        if folder_name in existing_folders:
            return existing_folders[folder_name]
        
        # Si no existe, crearla
        folder_id = self.create_folder(folder_name, parent_folder_id)
        if not folder_id:
            raise Exception(f"No se pudo crear la carpeta '{folder_name}'")
            
        return folder_id
    
    def list_folders(self, parent_folder_id: str) -> Dict[str, str]:
        """Lista solo las carpetas dentro de una carpeta padre"""
        query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        folder_list = self.drive.ListFile({'q': query}).GetList()
        return {folder['title']: folder['id'] for folder in folder_list}
    
    def upload_file(
        self,
        file_name: str,
        content: Union[str, bytes, BinaryIO],
        folder_id: str,
        mime_type: str = 'application/json'
    ) -> Optional[str]:
        """
        Sube un archivo a Google Drive
        
        Args:
            file_name: Nombre del archivo
            content: Contenido del archivo (string, bytes o file-like object)
            folder_id: ID de la carpeta destino
            mime_type: Tipo MIME del archivo
            
        Returns:
            URL del archivo subido o None si falla
        """
        try:
            # Convertir contenido a bytes si es necesario
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
            elif isinstance(content, bytes):
                content_bytes = content
            else:
                content_bytes = content.read()
            
            # Buscar si el archivo ya existe
            existing_files = self.list_files(folder_id)
            file_id = existing_files.get(file_name)
            
            if file_id:
                # Actualizar archivo existente
                file = self.drive.CreateFile({'id': file_id})
                file.SetContentString(content_bytes.decode('utf-8') if mime_type == 'application/json' else '')
                file.Upload()
                logger.info(f"Archivo '{file_name}' actualizado")
            else:
                # Crear nuevo archivo
                file_metadata = {
                    'title': file_name,
                    'parents': [{'id': folder_id}],
                    'mimeType': mime_type
                }
                file = self.drive.CreateFile(file_metadata)
                file.SetContentString(content_bytes.decode('utf-8') if mime_type == 'application/json' else '')
                file.Upload()
                logger.info(f"Archivo '{file_name}' creado")
            
            # Hacer el archivo público y obtener link
            file.InsertPermission({
                'type': 'anyone',
                'value': 'anyone',
                'role': 'reader'
            })
            
            return file['alternateLink']
        except Exception as e:
            logger.error(f"Error subiendo archivo: {e}")
            return None
    
    def download_file(self, file_id: str) -> Optional[bytes]:
        """
        Descarga un archivo de Google Drive
        
        Args:
            file_id: ID del archivo
            
        Returns:
            Contenido del archivo en bytes o None si falla
        """
        try:
            # Verificar caché
            if file_id in self._file_cache:
                return self._file_cache[file_id]
            
            file = self.drive.CreateFile({'id': file_id})
            content = file.GetContentString()
            content_bytes = content.encode('utf-8')
            
            # Guardar en caché
            self._file_cache[file_id] = content_bytes
            
            return content_bytes
        except Exception as e:
            logger.error(f"Error descargando archivo: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Elimina un archivo de Google Drive
        
        Args:
            file_id: ID del archivo
            
        Returns:
            True si se eliminó correctamente, False si falló
        """
        try:
            file = self.drive.CreateFile({'id': file_id})
            file.Trash()  # Mover a papelera en lugar de eliminar permanentemente
            
            # Limpiar caché
            if file_id in self._file_cache:
                del self._file_cache[file_id]
                
            logger.info(f"Archivo {file_id} movido a papelera")
            return True
        except Exception as e:
            logger.error(f"Error eliminando archivo: {e}")
            return False
    
    def search_files(
        self, 
        query: str, 
        folder_id: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, str]:
        """
        Busca archivos por nombre o contenido
        
        Args:
            query: Término de búsqueda
            folder_id: Limitar búsqueda a una carpeta específica
            limit: Número máximo de resultados
            
        Returns:
            Diccionario {nombre_archivo: id_archivo}
        """
        try:
            search_query = f"fullText contains '{query}' and trashed=false"
            if folder_id:
                search_query = f"'{folder_id}' in parents and {search_query}"
            
            file_list = self.drive.ListFile({
                'q': search_query,
                'maxResults': limit
            }).GetList()
            
            return {file['title']: file['id'] for file in file_list}
        except Exception as e:
            logger.error(f"Error buscando archivos: {e}")
            return {}
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene metadatos de un archivo"""
        try:
            file = self.drive.CreateFile({'id': file_id})
            file.FetchMetadata()
            
            return {
                'title': file['title'],
                'mimeType': file['mimeType'],
                'fileSize': file.get('fileSize', 0),
                'createdDate': file['createdDate'],
                'modifiedDate': file['modifiedDate'],
                'alternateLink': file['alternateLink']
            }
        except Exception as e:
            logger.error(f"Error obteniendo metadatos: {e}")
            return None
    
    def clear_cache(self):
        """Limpia la caché de archivos"""
        self._file_cache.clear()
        logger.info("Caché de archivos limpiada") 