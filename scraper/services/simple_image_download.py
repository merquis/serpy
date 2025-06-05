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
    
    async def trigger_download(self, mongo_id: str) -> Dict[str, Any]:
        """
        Ejecuta el curl dinámico y devuelve el comando usado
        
        Args:
            mongo_id: ID del documento en MongoDB
            
        Returns:
            Respuesta del servicio y el comando curl usado
        """
        try:
            url = "https://images.serpsrewrite.com/api/v1/download/from-api-url-simple"
            params = {
                "api_url": f"https://api.serpsrewrite.com/hotel-booking/{mongo_id}"
            }
            headers = {
                "X-API-Key": "serpy-demo-key-2025"
            }
            curl_cmd = f'curl -X POST "{url}?api_url={params["api_url"]}" -H "X-API-Key: {headers["X-API-Key"]}"'
            logger.info(f"Ejecutando comando equivalente a: {curl_cmd}")
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    url,
                    params=params,
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
                        "curl_cmd": curl_cmd
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text,
                        "mongo_id": mongo_id,
                        "curl_cmd": curl_cmd
                    }
        except Exception as e:
            logger.error(f"Error al ejecutar descarga: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "mongo_id": mongo_id,
                "curl_cmd": curl_cmd if 'curl_cmd' in locals() else ""
            }
