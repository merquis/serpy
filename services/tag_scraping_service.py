"""
Servicio de Tag Scraping - Extracción de estructura HTML
Con optimización usando HTTPX primero y Playwright como fallback
"""
import asyncio
from typing import List, Dict, Any, Optional
import logging
from services.utils import PlaywrightService, PlaywrightConfig
from services.utils.httpx_service import HttpxService, create_stealth_httpx_config
from config import config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""
    
    def __init__(self):
        # Configuración específica para tag scraping con Playwright
        self.playwright_config = PlaywrightConfig(
            wait_until="networkidle",
            timeout=30000
        )
        self.playwright_service = PlaywrightService(self.playwright_config)
        
        # Configuración para HTTPX con medidas anti-bot
        self.httpx_config = create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
    
    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrae la estructura de etiquetas de URLs contenidas en JSON
        
        Args:
            json_data: Datos JSON con URLs (puede ser dict o list)
            max_concurrent: Número máximo de scrapers concurrentes
            progress_callback: Función callback para actualizar progreso
            
        Returns:
            Lista de resultados con estructura de etiquetas
        """
        # Convertir a lista si es necesario
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []
        
        # Calcular total de URLs para progreso
        total_urls = 0
        for item in data_list:
            if isinstance(item, dict):
                total_urls += len(self._extract_urls_from_item(item))
        
        urls_processed = 0
        
        for item in data_list:
            if not isinstance(item, dict):
                continue
            
            # Extraer contexto
            context = {
                "busqueda": item.get("busqueda", ""),
                "idioma": item.get("idioma", ""),
                "region": item.get("region", ""),
                "dominio": item.get("dominio", ""),
                "url_busqueda": item.get("url_busqueda", "")
            }
            
            # Extraer URLs
            urls = self._extract_urls_from_item(item)
            
            if urls:
                # Función para procesar cada URL con HTTPX o navegador
                async def process_tag_structure(url: str, html: str, method_or_browser) -> Dict[str, Any]:
                    try:
                        # Si es string, es el método (httpx)
                        if isinstance(method_or_browser, str):
                            # Procesar con BeautifulSoup para httpx
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extraer título
                            title_tag = soup.find('title')
                            title = title_tag.text.strip() if title_tag else ""
                            
                            # Extraer estructura de headings
                            h1_structure = self._extract_headings_from_soup(soup)
                            
                            return {
                                "url": url,
                                "status_code": 200,
                                "title": title,
                                "h1": h1_structure,
                                "method": "httpx"  # Indicar que se usó httpx
                            }
                        else:
                            # Es un browser de Playwright
                            page = await method_or_browser.new_page()
                            try:
                                await page.set_content(html)
                                
                                # Extraer título
                                title = await page.title()
                                
                                # Extraer estructura de headings
                                h1_structure = await self.playwright_service.execute_javascript(
                                    page, 
                                    self._get_heading_extraction_script()
                                )
                                
                                return {
                                    "url": url,
                                    "status_code": 200,
                                    "title": title,
                                    "h1": h1_structure,
                                    "method": "playwright"  # Indicar que se usó Playwright
                                }
                            finally:
                                await page.close()
                    except Exception as e:
                        logger.error(f"Error procesando estructura de {url}: {e}")
                        return {
                            "url": url,
                            "status_code": "error",
                            "error": str(e),
                            "method": method_or_browser if isinstance(method_or_browser, str) else "playwright"
                        }
                
                # Crear callback personalizado
                def enhanced_progress_callback(info):
                    if progress_callback:
                        # Pasar información de progreso directamente
                        if isinstance(info, dict) and "active_urls" in info:
                            progress_callback(info)
                
                # Procesar URLs usando HTTPX con fallback a Playwright
                results = await self.httpx_service.process_urls_batch_with_fallback(
                    urls=urls,
                    process_func=process_tag_structure,
                    playwright_service=self.playwright_service,
                    config=self.httpx_config,
                    playwright_config=self.playwright_config,
                    max_concurrent=max_concurrent,
                    progress_callback=enhanced_progress_callback
                )
                
                urls_processed += len(urls)
                
                all_results.append({
                    **context,
                    "resultados": results
                })
        
        return all_results
    
    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        """Extrae todas las URLs de un item del JSON"""
        urls = []
        
        # Buscar en campo 'urls'
        if "urls" in item:
            for url_item in item["urls"]:
                if isinstance(url_item, str):
                    urls.append(url_item)
                elif isinstance(url_item, dict) and "url" in url_item:
                    urls.append(url_item["url"])
        
        # Buscar en campo 'resultados'
        if "resultados" in item:
            for result in item["resultados"]:
                if isinstance(result, dict) and "url" in result:
                    urls.append(result["url"])
        
        return urls
    
    def _get_heading_extraction_script(self) -> str:
        """Retorna el script JavaScript para extraer la estructura de headings"""
        return """
            () => {
                const h1 = document.querySelector('h1');
                if (!h1) return {};
                
                const result = {
                    titulo: h1.textContent.trim(),
                    level: 'h1',
                    h2: []
                };
                
                // Función para obtener el contenido entre dos elementos
                function getContentBetween(start, end) {
                    const content = [];
                    let current = start.nextElementSibling;
                    
                    while (current && current !== end) {
                        if (current.tagName === 'P') {
                            content.push(current.textContent.trim());
                        }
                        current = current.nextElementSibling;
                    }
                    
                    return content.join(' ');
                }
                
                // Buscar todos los elementos después del H1
                let currentElement = h1.nextElementSibling;
                let currentH2 = null;
                
                while (currentElement) {
                    if (currentElement.tagName === 'H1') {
                        break;
                    } else if (currentElement.tagName === 'H2') {
                        currentH2 = {
                            titulo: currentElement.textContent.trim(),
                            level: 'h2',
                            h3: []
                        };
                        result.h2.push(currentH2);
                    } else if (currentElement.tagName === 'H3' && currentH2) {
                        currentH2.h3.push({
                            titulo: currentElement.textContent.trim(),
                            level: 'h3'
                        });
                    }
                    
                    currentElement = currentElement.nextElementSibling;
                }
                
                return result;
            }
        """
    
    def _extract_headings_from_soup(self, soup) -> Dict[str, Any]:
        """Extrae la estructura de headings usando BeautifulSoup"""
        h1 = soup.find('h1')
        if not h1:
            return {}
        
        result = {
            "titulo": h1.get_text(strip=True),
            "level": "h1",
            "h2": []
        }
        
        # Encontrar todos los elementos después del H1
        current = h1.next_sibling
        current_h2 = None
        
        while current:
            if hasattr(current, 'name'):
                if current.name == 'h1':
                    break
                elif current.name == 'h2':
                    current_h2 = {
                        "titulo": current.get_text(strip=True),
                        "level": "h2",
                        "h3": []
                    }
                    result["h2"].append(current_h2)
                elif current.name == 'h3' and current_h2:
                    current_h2["h3"].append({
                        "titulo": current.get_text(strip=True),
                        "level": "h3"
                    })
            
            current = current.next_sibling
        
        return result
