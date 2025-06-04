"""
Servicio de descarga de imágenes con control de concurrencia
"""
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
import httpx
from PIL import Image
import io
import time
from collections import defaultdict

from app.core import logger, settings
from app.core.exceptions import DownloadException
from app.models.domain import ImageInfo, calculate_bytes_hash


class ImageDownloader:
    """Servicio para descargar imágenes con control de concurrencia"""
    
    def __init__(
        self,
        max_concurrent_downloads: int = None,
        max_connections_per_host: int = None,
        timeout: int = None,
        max_retries: int = None,
        retry_delay: int = None
    ):
        self.max_concurrent_downloads = max_concurrent_downloads or settings.max_concurrent_downloads
        self.max_connections_per_host = max_connections_per_host or settings.max_connections_per_host
        self.timeout = timeout or settings.download_timeout
        self.max_retries = max_retries or settings.max_retries
        self.retry_delay = retry_delay or settings.retry_delay
        
        # Semáforos para control de concurrencia
        self._global_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        self._host_semaphores: Dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(self.max_connections_per_host)
        )
        
        # Cliente HTTP
        self._client: Optional[httpx.AsyncClient] = None
        
        # Estadísticas
        self.stats = {
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "total_bytes": 0,
            "total_time": 0.0
        }
    
    async def __aenter__(self):
        """Inicializa el cliente HTTP"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30
            ),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra el cliente HTTP"""
        if self._client:
            await self._client.aclose()
    
    def _get_host_from_url(self, url: str) -> str:
        """Extrae el host de una URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return "unknown"
    
    async def download_image(self, url: str, filename: str = None) -> Tuple[bytes, ImageInfo]:
        """
        Descarga una imagen individual
        
        Returns:
            Tuple de (contenido_bytes, ImageInfo)
        """
        if not self._client:
            raise DownloadException("Cliente HTTP no inicializado")
        
        host = self._get_host_from_url(url)
        host_semaphore = self._host_semaphores[host]
        
        # Control de concurrencia
        async with self._global_semaphore:
            async with host_semaphore:
                return await self._download_with_retry(url, filename)
    
    async def _download_with_retry(self, url: str, filename: str = None) -> Tuple[bytes, ImageInfo]:
        """Descarga con reintentos"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                logger.debug("Descargando imagen", url=url, attempt=attempt + 1)
                
                # Realizar descarga
                response = await self._client.get(url)
                response.raise_for_status()
                
                # Obtener contenido
                content = response.content
                
                # Validar que es una imagen
                image_info = await self._validate_and_get_info(content, url, filename)
                
                # Actualizar estadísticas
                download_time = time.time() - start_time
                self.stats["total_downloads"] += 1
                self.stats["successful_downloads"] += 1
                self.stats["total_bytes"] += len(content)
                self.stats["total_time"] += download_time
                
                logger.info(
                    "Imagen descargada exitosamente",
                    url=url,
                    size_mb=round(len(content) / (1024 * 1024), 2),
                    time=round(download_time, 2)
                )
                
                return content, image_info
                
            except httpx.HTTPStatusError as e:
                last_error = f"Error HTTP {e.response.status_code}: {e.response.text[:200]}"
                logger.warning("Error HTTP descargando imagen", url=url, status=e.response.status_code)
                
            except httpx.TimeoutException:
                last_error = f"Timeout después de {self.timeout} segundos"
                logger.warning("Timeout descargando imagen", url=url)
                
            except Exception as e:
                last_error = str(e)
                logger.warning("Error descargando imagen", url=url, error=str(e))
            
            # Esperar antes de reintentar (backoff exponencial)
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)
        
        # Si llegamos aquí, todos los reintentos fallaron
        self.stats["total_downloads"] += 1
        self.stats["failed_downloads"] += 1
        
        error_msg = f"Fallo después de {self.max_retries} intentos: {last_error}"
        logger.error("Descarga fallida definitivamente", url=url, error=error_msg)
        
        # Devolver ImageInfo con error
        image_info = ImageInfo(
            filename=filename or self._get_filename_from_url(url),
            url=url,
            size_bytes=0,
            mime_type="unknown",
            width=0,
            height=0,
            hash="",
            downloaded_at=datetime.utcnow(),
            error=error_msg
        )
        
        raise DownloadException(error_msg, url=url)
    
    async def _validate_and_get_info(self, content: bytes, url: str, filename: str = None) -> ImageInfo:
        """Valida que el contenido es una imagen y obtiene su información"""
        try:
            # Abrir imagen con PIL para validar y obtener info
            img = Image.open(io.BytesIO(content))
            
            # Obtener información
            width, height = img.size
            mime_type = f"image/{img.format.lower()}" if img.format else "image/unknown"
            
            # Calcular hash
            content_hash = calculate_bytes_hash(content)
            
            # Generar nombre de archivo si no se proporciona
            if not filename:
                filename = self._get_filename_from_url(url)
                if not filename or filename == "image":
                    # Usar hash como nombre si no hay nombre válido
                    ext = img.format.lower() if img.format else "jpg"
                    filename = f"{content_hash[:8]}.{ext}"
            
            return ImageInfo(
                filename=filename,
                url=url,
                size_bytes=len(content),
                mime_type=mime_type,
                width=width,
                height=height,
                hash=content_hash,
                downloaded_at=datetime.utcnow()
            )
            
        except Exception as e:
            raise DownloadException(f"Contenido no es una imagen válida: {str(e)}", url=url)
    
    def _get_filename_from_url(self, url: str) -> str:
        """Extrae el nombre de archivo de una URL"""
        try:
            from urllib.parse import urlparse, unquote
            path = urlparse(url).path
            filename = path.split('/')[-1]
            filename = unquote(filename)
            
            # Validar que tiene extensión de imagen
            valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'}
            if any(filename.lower().endswith(ext) for ext in valid_extensions):
                return filename
            
            return "image"
        except Exception:
            return "image"
    
    async def download_batch(
        self,
        urls: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[Tuple[Optional[bytes], ImageInfo]]:
        """
        Descarga un lote de imágenes
        
        Args:
            urls: Lista de URLs a descargar
            progress_callback: Función callback(processed, total, current_url)
            
        Returns:
            Lista de tuplas (content, ImageInfo). Si falla, content es None
        """
        results = []
        total = len(urls)
        
        # Crear tareas de descarga
        tasks = []
        for i, url in enumerate(urls):
            filename = f"img_{i+1:03d}{self._get_extension_from_url(url)}"
            task = self._download_with_progress(url, filename, i, total, progress_callback)
            tasks.append(task)
        
        # Ejecutar todas las descargas concurrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar resultados
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                # La descarga falló, pero ya tenemos el ImageInfo con error
                processed_results.append((None, result))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _download_with_progress(
        self,
        url: str,
        filename: str,
        index: int,
        total: int,
        progress_callback: Optional[callable]
    ) -> Tuple[Optional[bytes], ImageInfo]:
        """Descarga con callback de progreso"""
        try:
            content, image_info = await self.download_image(url, filename)
            
            if progress_callback:
                await progress_callback(index + 1, total, url)
            
            return content, image_info
            
        except DownloadException as e:
            # Crear ImageInfo con error
            image_info = ImageInfo(
                filename=filename,
                url=url,
                size_bytes=0,
                mime_type="unknown",
                width=0,
                height=0,
                hash="",
                downloaded_at=datetime.utcnow(),
                error=str(e)
            )
            
            if progress_callback:
                await progress_callback(index + 1, total, url)
            
            return None, image_info
    
    def _get_extension_from_url(self, url: str) -> str:
        """Obtiene la extensión del archivo desde la URL"""
        filename = self._get_filename_from_url(url)
        if '.' in filename:
            return '.' + filename.split('.')[-1].lower()
        return '.jpg'  # Por defecto
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de descarga"""
        stats = self.stats.copy()
        
        # Calcular promedios
        if stats["successful_downloads"] > 0:
            stats["average_size_mb"] = round(
                (stats["total_bytes"] / stats["successful_downloads"]) / (1024 * 1024), 2
            )
            stats["average_time"] = round(
                stats["total_time"] / stats["successful_downloads"], 2
            )
        else:
            stats["average_size_mb"] = 0
            stats["average_time"] = 0
        
        stats["total_size_mb"] = round(stats["total_bytes"] / (1024 * 1024), 2)
        stats["success_rate"] = round(
            (stats["successful_downloads"] / stats["total_downloads"] * 100) 
            if stats["total_downloads"] > 0 else 0, 2
        )
        
        return stats
