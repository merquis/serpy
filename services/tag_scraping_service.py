"""
Servicio de Tag Scraping - Extracción de estructura HTML
"""
import asyncio
from typing import List, Dict, Any, Optional
import logging
from services.utils import PlaywrightService, PlaywrightConfig
from config import config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""
    
    def __init__(self):
        # Configuración específica para tag scraping
        config = PlaywrightConfig(
            wait_until="networkidle",
            timeout=30000
        )
        self.playwright_service = PlaywrightService(config)
    
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
                # Función para procesar cada URL
                async def process_tag_structure(url: str, html: str, browser) -> Dict[str, Any]:
                    # Crear una página temporal para ejecutar JavaScript
                    page = await browser.new_page()
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
                            "status_code": 200,  # Si llegamos aquí, asumimos éxito
                            "title": title,
                            "h1": h1_structure
                        }
                    finally:
                        await page.close()
                
                # Crear callback personalizado que incluya el progreso total
                def enhanced_progress_callback(info):
                    nonlocal urls_processed
                    if progress_callback:
                        progress_callback({
                            "current_info": info,
                            "urls_processed": urls_processed,
                            "total_urls": total_urls,
                            "search_term": context.get("busqueda", "")
                        })
                
                # Procesar URLs usando el servicio base
                results = await self.playwright_service.process_urls_batch(
                    urls=urls,
                    process_func=process_tag_structure,
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
