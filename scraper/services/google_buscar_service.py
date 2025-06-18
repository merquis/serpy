"""
Servicio de Scraping - Lógica de negocio para scraping de URLs
"""
import urllib.parse
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any, Optional, Tuple
from config.settings import settings
import logging
from services.utils.httpx_service import HttpxService, create_fast_httpx_config, create_stealth_httpx_config, httpx_requests
# from services.utils.playwright_service import PlaywrightService, PlaywrightConfig
import asyncio
import httpx

logger = logging.getLogger(__name__)

class GoogleBuscarService:
    """Servicio para scraping de resultados de Google"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.brightdata_token
        self.api_url = "https://api.brightdata.com/request"
        # Inicializar servicio httpx
        self.httpx_config = create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
        # self.playwright_config = PlaywrightConfig()
        # self.playwright_service = PlaywrightService(self.playwright_config)
        
    def search_multiple_queries(
        self,
        queries: List[str],
        num_results: int = 10,
        language_code: str = "es",
        region_code: str = "es",
        google_domain: str = "google.es"
    ) -> List[Dict[str, Any]]:
        """
        Realiza búsquedas múltiples en Google
        
        Args:
            queries: Lista de términos de búsqueda
            num_results: Número de resultados por consulta
            language_code: Código de idioma (ej: es, en-GB)
            region_code: Código de región (ej: es, uk)
            google_domain: Dominio de Google a usar
            
        Returns:
            Lista de resultados con URLs para cada búsqueda
        """
        results = []
        
        for query in queries:
            try:
                result = self._search_single_query(
                    query, 
                    num_results, 
                    language_code, 
                    region_code, 
                    google_domain
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error en búsqueda '{query}': {e}")
                results.append({
                    "busqueda": query,
                    "error": str(e),
                    "urls": []
                })
        
        return results
    
    def _search_single_query(
        self,
        query: str,
        num_results: int,
        language_code: str,
        region_code: str,
        google_domain: str
    ) -> Dict[str, Any]:
        """Realiza una búsqueda individual en Google"""
        urls = []
        encoded_query = urllib.parse.quote(query)
        
        step = settings.step_size or 10
        i = 0
        max_attempts = 10
        while len(urls) < num_results and i < max_attempts:
            start = i * step
            i += 1
            search_url = self._build_search_url(
                encoded_query, 
                language_code, 
                region_code, 
                google_domain, 
                start
            )
            try:
                html_content = self._fetch_page(search_url)
                page_urls = self._extract_urls(html_content)
                urls.extend(page_urls)
                if len(urls) >= num_results:
                    break
            except Exception as e:
                logger.error(f"Error fetching page {start} for '{query}': {e}")
                break
        
        # Eliminar duplicados manteniendo el orden
        unique_urls = list(dict.fromkeys(urls[:num_results]))
        
        return {
            "busqueda": query,
            "idioma": language_code,
            "region": region_code,
            "dominio": google_domain,
            "url_busqueda": search_url,
            "urls": unique_urls
        }
    
    def _build_search_url(
        self, 
        query: str, 
        hl: str, 
        gl: str, 
        domain: str, 
        start: int
    ) -> str:
        """Construye la URL de búsqueda de Google"""
        return f"https://{domain}/search?q={query}&hl={hl}&gl={gl}&start={start}"
    
    def _fetch_page(self, url: str) -> str:
        """Obtiene el contenido HTML de una página usando BrightData"""
        payload = {
            "zone": "serppy",
            "url": url,
            "format": "raw"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            response = httpx_requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=settings.timeout
            )
            response.raise_for_status()
            html = response.text
            logger.debug(f"BrightData response status: {response.status_code}")
            logger.debug(f"BrightData HTML preview:\n{html[:1000]}")
            return html
        except Exception as e:
            logger.error(f"Error usando httpx con BrightData: {e}")
            raise
    
    def _extract_urls(self, html: str) -> List[str]:
        """Extrae URLs de los resultados de búsqueda"""
        soup = BeautifulSoup(html, "html.parser")
        urls = []

        # DEBUG: Mostrar parte del HTML para inspección
        preview = soup.prettify()[:1000]
        logger.debug(f"HTML Preview:\n{preview}")

        # Buscar <h3> y subir al <a> padre para extraer el href
        for h3 in soup.find_all("h3"):
            parent = h3.find_parent("a")
            if parent:
                href = parent.get("href")
                if href and href.startswith("http"):
                    urls.append(href)

        return urls
