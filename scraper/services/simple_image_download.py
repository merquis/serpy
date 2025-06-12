"""
Servicio simple para ejecutar el curl exacto de descarga de imágenes
"""
import logging
import httpx
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SimpleImageDownloadService:
    """Servicio simple para descargar imágenes con el curl exacto"""
    
    async def trigger_download(self, mongo_id: str, database_name: str = None, collection_name: str = None) -> Dict[str, Any]:
        """
        Ejecuta el curl dinámico y devuelve el comando usado
        
        Args:
            mongo_id: ID del documento en MongoDB
            database_name: Nombre de la base de datos (opcional)
            collection_name: Nombre de la colección (opcional)
            
        Returns:
            Respuesta del servicio y el comando curl usado
        """
        try:
            # Si no se proporciona collection_name, usar el default
            if not collection_name:
                collection_name = "hotel-booking"
            
            url = "https://images.serpsrewrite.com/api/v1/download/from-api-url-simple"
            
            # URLs de API a intentar en orden de prioridad
            api_urls = [
                "http://localhost:8000",  # API local
                "http://api:8000",        # API en Docker
                "https://api.serpsrewrite.com"  # API externa
            ]
            
            headers = {
                "X-API-Key": "serpy-demo-key-2025",
                "Content-Type": "application/json"
            }
            
            # Intentar cada URL hasta encontrar una que funcione
            last_error = None
            for api_base_url in api_urls:
                try:
                    json_data = {
                        "api_url": f"{api_base_url}/{collection_name}/{mongo_id}"
                    }
                    
                    # Añadir database_name si se proporciona
                    if database_name:
                        json_data["database_name"] = database_name
                    
                    # Añadir collection_name
                    json_data["collection_name"] = collection_name
                    
                    # Construir comando curl con JSON body
                    import json
                    curl_cmd = f'curl -X POST "{url}" -H "X-API-Key: {headers["X-API-Key"]}" -H "Content-Type: application/json" -d \'{json.dumps(json_data)}\''
                    
                    logger.info(f"Intentando API: {api_base_url}")
                    logger.info(f"Comando curl equivalente: {curl_cmd}")
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            url,
                            json=json_data,
                            headers=headers
                        )
                        logger.info(f"Status Code: {response.status_code}")
                        logger.info(f"Response: {response.text}")
                        
                        if response.status_code == 200:
                            return {
                                "success": True,
                                "status_code": response.status_code,
                                "response": response.json() if response.text else {},
                                "mongo_id": mongo_id,
                                "curl_cmd": curl_cmd,
                                "api_used": api_base_url
                            }
                        else:
                            last_error = f"API {api_base_url} respondió con status {response.status_code}: {response.text}"
                            logger.warning(last_error)
                            continue
                            
                except Exception as e:
                    last_error = f"Error conectando a API {api_base_url}: {str(e)}"
                    logger.warning(last_error)
                    continue
            
            # Si llegamos aquí, ninguna API funcionó
            return {
                "success": False,
                "status_code": 503,
                "error": f"Ninguna API disponible. Último error: {last_error}",
                "mongo_id": mongo_id,
                "curl_cmd": curl_cmd if 'curl_cmd' in locals() else "",
                "apis_tried": api_urls
            }
        except Exception as e:
            logger.error(f"Error al ejecutar descarga: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "mongo_id": mongo_id,
                "curl_cmd": curl_cmd if 'curl_cmd' in locals() else ""
            }
