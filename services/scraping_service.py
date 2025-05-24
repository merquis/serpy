"""
Servicio de Scraping - Lógica de negocio para scraping de URLs
"""
import urllib.parse
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Any, Optional, Tuple
from config import config
import logging
from services.utils.httpx_service import HttpxService, create_fast_httpx_config, create_stealth_httpx_config
from services.utils.playwright_service import PlaywrightService, PlaywrightConfig
import asyncio
import httpx

logger = logging.getLogger(__name__)

class GoogleScrapingService:
    """Servicio para scraping de resultados de Google"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or config.brightdata_token
        self.api_url = "https://api.brightdata.com/request"
        # Inicializar servicio httpx
        self.httpx_config = create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
        self.playwright_config = PlaywrightConfig()
        self.playwright_service = PlaywrightService(self.playwright_config)
        
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
        
        for start in range(0, num_results, config.scraping.step_size):
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
        
        response = self.httpx_service.post_sync(
            self.api_url, 
            headers=headers, 
            json=payload,  # httpx acepta json directamente
            timeout=config.scraping.timeout
        )
        
        response.raise_for_status()
        return response.text
    
    def _extract_urls(self, html: str) -> List[str]:
        """Extrae URLs de los resultados de búsqueda"""
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        
        # Buscar enlaces que contienen h3 (títulos de resultados)
        for link in soup.select("a:has(h3)"):
            href = link.get("href")
            if href and href.startswith("http"):
                urls.append(href)
        
        return urls

class TagScrapingService:
    """Servicio para scraping de etiquetas HTML de páginas web"""
    
    def __init__(self):
        # Inicializar servicio httpx
        self.httpx_config = create_fast_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
        self.playwright_config = PlaywrightConfig()
        self.playwright_service = PlaywrightService(self.playwright_config)
    
    async def scrape_tags_from_urls(
        self,
        urls: List[str],
        extract_content: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extrae la estructura de etiquetas H1, H2, H3 de múltiples URLs
        
        Args:
            urls: Lista de URLs a analizar
            extract_content: Si debe extraer el contenido de texto además del título
            
        Returns:
            Lista de resultados con la estructura de etiquetas para cada URL
        """
        results = []
        
        async def process_func(url: str, html: str, method: str) -> Dict[str, Any]:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            title = soup.find("title")
            title_text = title.text.strip() if title else ""

            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc.get("content", "").strip() if meta_desc else ""

            h1_data = self._extract_h1_structure(soup, extract_content)

            if not h1_data:
                all_headers = []
                for level in ['h1', 'h2', 'h3']:
                    headers = soup.find_all(level)
                    for header in headers:
                        all_headers.append({
                            "level": level,
                            "text": header.text.strip()
                        })
                if all_headers:
                    h1_data = {"headers": all_headers}

            return {
                "url": url,
                "status_code": 200,
                "title": title_text,
                "description": description,
                "h1": h1_data,
                "method": method
            }

        results = await self.httpx_service.process_urls_batch_with_fallback(
            urls=urls,
            process_func=process_func,
            playwright_service=self.playwright_service,
            config=self.httpx_config,
            playwright_config=self.playwright_config,
            max_concurrent=5
        )
        
        return results
    
    def _scrape_single_url(
        self, 
        url: str, 
        extract_content: bool
    ) -> Dict[str, Any]:
        """Extrae etiquetas de una URL individual"""
        result, html = self.httpx_service.get_html_sync(url, timeout=config.scraping.timeout)
        
        # Si httpx no pudo obtener el contenido, devolver error
        if not result.get('success') or not html:
            return {
                "url": url,
                "error": result.get('error', 'Error desconocido'),
                "status_code": result.get('status_code', 0),
                "needs_playwright": result.get('needs_playwright', False),
                "method": result.get('method', 'httpx')
            }
        
        # Si tenemos contenido HTML, procesarlo
        soup = BeautifulSoup(html, "html.parser")
        
        # Extraer título de la página
        title = soup.find("title")
        title_text = title.text.strip() if title else ""
        
        # Extraer meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        description = ""
        if meta_desc and hasattr(meta_desc, 'get'):
            description = meta_desc.get("content", "").strip()
        
        # Extraer H1
        h1_data = self._extract_h1_structure(soup, extract_content)
        
        # Si no hay H1, intentar extraer todos los headers disponibles
        if not h1_data:
            # Buscar cualquier header (h1, h2, h3)
            all_headers = []
            for level in ['h1', 'h2', 'h3']:
                headers = soup.find_all(level)
                for header in headers:
                    all_headers.append({
                        "level": level,
                        "text": header.text.strip()
                    })
            
            # Si encontramos headers, devolverlos
            if all_headers:
                h1_data = {"headers": all_headers}
        
        return {
            "url": url,
            "status_code": result.get('status_code', 200),
            "title": title_text,
            "description": description,
            "h1": h1_data,
            "method": result.get('method', 'httpx')
        }
    
    def _extract_h1_structure(
        self, 
        soup: BeautifulSoup, 
        extract_content: bool
    ) -> Dict[str, Any]:
        """Extrae la estructura completa H1 -> H2 -> H3"""
        h1 = soup.find("h1")
        if not h1:
            return {}
        
        h1_data = {
            "titulo": h1.text.strip(),
            "level": "h1",
            "h2": []
        }
        
        if extract_content:
            h1_data["contenido"] = self._extract_content_until_next_heading(h1)
        
        # Buscar todos los H2 después del H1
        current = h1.find_next_sibling()
        current_h2 = None
        
        while current:
            if current.name == "h1":
                break
            elif current.name == "h2":
                h2_data = {
                    "titulo": current.text.strip(),
                    "level": "h2",
                    "h3": []
                }
                if extract_content:
                    h2_data["contenido"] = self._extract_content_until_next_heading(current)
                h1_data["h2"].append(h2_data)
                current_h2 = h2_data
            elif current.name == "h3" and current_h2:
                h3_data = {
                    "titulo": current.text.strip(),
                    "level": "h3"
                }
                if extract_content:
                    h3_data["contenido"] = self._extract_content_until_next_heading(current)
                current_h2["h3"].append(h3_data)
            
            current = current.find_next_sibling()
        
        return h1_data
    
    def _extract_content_until_next_heading(self, element) -> str:
        """Extrae el contenido de texto entre el elemento actual y el siguiente heading"""
        content = []
        current = element.find_next_sibling()
        
        while current and current.name not in ["h1", "h2", "h3"]:
            if current.name == "p":
                content.append(current.text.strip())
            current = current.find_next_sibling()
        
        return " ".join(content)
