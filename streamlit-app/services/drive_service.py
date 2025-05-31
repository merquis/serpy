"""
Servicio de Google Drive - Gestión mejorada de archivos y carpetas
"""
from typing import Dict, List, Optional, Union, BinaryIO, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from io import BytesIO
import json
import logging
import streamlit as st

logger = logging.getLogger(__name__)

class DriveService:
    """Servicio mejorado para interactuar con Google Drive"""
    
    def __init__(self):
        self._service = None
        self._file_cache = {}
        
    def _get_service(self):
        """Obtiene o crea el servicio de Google Drive"""
        if self._service is None:
            try:
                creds = service_account.Credentials.from_service_account_info(
                    dict(st.secrets["drive_service_account"]),
                    scopes=['https://www.googleapis.com/auth/drive']
                )
                self._service = build("drive", "v3", credentials=creds)
            except Exception as e:
                logger.error(f"Error inicializando Google Drive: {e}")
                raise
        return self._service
    
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
            service = self._get_service()
            query = f"'{folder_id}' in parents and trashed=false"
            if file_type:
                query += f" and mimeType='{file_type}'"
                
            results = service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=limit
            ).execute()
            
            files = results.get('files', [])
            return {file['name']: file['id'] for file in files}
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
            service = self._get_service()
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            
            folder = service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
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
        try:
            service = self._get_service()
            query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            results = service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            return {folder['name']: folder['id'] for folder in folders}
        except Exception as e:
            logger.error(f"Error listando carpetas: {e}")
            return {}
    
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
            service = self._get_service()
            
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
            
            media = MediaIoBaseUpload(BytesIO(content_bytes), mimetype=mime_type)
            
            if file_id:
                # Actualizar archivo existente
                file = service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                logger.info(f"Archivo '{file_name}' actualizado")
            else:
                # Crear nuevo archivo
                file_metadata = {
                    'name': file_name,
                    'parents': [folder_id],
                    'mimeType': mime_type
                }
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink'
                ).execute()
                logger.info(f"Archivo '{file_name}' creado")
            
            return file.get('webViewLink')
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
            
            service = self._get_service()
            request = service.files().get_media(fileId=file_id)
            
            buffer = BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            content_bytes = buffer.getvalue()
            
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
            service = self._get_service()
            service.files().delete(fileId=file_id).execute()
            
            # Limpiar caché
            if file_id in self._file_cache:
                del self._file_cache[file_id]
                
            logger.info(f"Archivo {file_id} eliminado")
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
            service = self._get_service()
            search_query = f"fullText contains '{query}' and trashed=false"
            if folder_id:
                search_query = f"'{folder_id}' in parents and {search_query}"
            
            results = service.files().list(
                q=search_query,
                fields="files(id, name)",
                pageSize=limit
            ).execute()
            
            files = results.get('files', [])
            return {file['name']: file['id'] for file in files}
        except Exception as e:
            logger.error(f"Error buscando archivos: {e}")
            return {}
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene metadatos de un archivo"""
        try:
            service = self._get_service()
            file = service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, size, createdTime, modifiedTime, webViewLink'
            ).execute()
            
            return {
                'id': file['id'],
                'name': file['name'],
                'mimeType': file['mimeType'],
                'size': file.get('size', 0),
                'createdTime': file['createdTime'],
                'modifiedTime': file['modifiedTime'],
                'webViewLink': file.get('webViewLink')
            }
        except Exception as e:
            logger.error(f"Error obteniendo metadatos: {e}")
            return None
    
    def clear_cache(self):
        """Limpia la caché de archivos"""
        self._file_cache.clear()
        logger.info("Caché de archivos limpiada")
    
    def list_json_files_in_folder(self, folder_id: str) -> Dict[str, str]:
        """
        Lista archivos JSON en una carpeta
        
        Args:
            folder_id: ID de la carpeta
            
        Returns:
            Diccionario {nombre_archivo: id_archivo}
        """
        return self.list_files(folder_id, file_type='application/json')
    
    def get_file_content(self, file_id: str) -> Optional[bytes]:
        """
        Obtiene el contenido de un archivo (alias de download_file)
        
        Args:
            file_id: ID del archivo
            
        Returns:
            Contenido del archivo en bytes
        """
        return self.download_file(file_id) 