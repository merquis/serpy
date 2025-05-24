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
                            
                            # Extraer meta description
                            meta_desc = soup.find('meta', attrs={'name': 'description'})
                            description = meta_desc.get('content', '').strip() if meta_desc else ""
                            
                            # Extraer primer h1
                            first_h1 = soup.find('h1')
                            primer_h1 = first_h1.text.strip() if first_h1 else ""
                            
                            # Extraer estructura completa de headings
                            estructura_headings = self._extract_headings_from_soup(soup)
                            
                            return {
                                "url": url,
                                "status_code": 200,
                                "title": title,
                                "description": description,
                                "primer_h1": primer_h1,
                                "estructura_completa": estructura_headings,
                                "method": "httpx"  # Indicar que se usó httpx
                            }
                        else:
                            # Es un browser de Playwright
                            page = await method_or_browser.new_page()
                            try:
                                await page.set_content(html)
                                
                                # Extraer título
                                title = await page.title()
                                
                                # Extraer meta description
                                description = await page.evaluate("""
                                    () => {
                                        const metaDesc = document.querySelector('meta[name="description"]');
                                        return metaDesc ? metaDesc.content.trim() : "";
                                    }
                                """)
                                
                                # Extraer primer h1
                                primer_h1 = await page.evaluate("""
                                    () => {
                                        const firstH1 = document.querySelector('h1');
                                        return firstH1 ? firstH1.textContent.trim() : "";
                                    }
                                """)
                                
                                # Extraer estructura completa de headings
                                estructura_headings = await self.playwright_service.execute_javascript(
                                    page, 
                                    self._get_heading_extraction_script()
                                )
                                
                                return {
                                    "url": url,
                                    "status_code": 200,
                                    "title": title,
                                    "description": description,
                                    "primer_h1": primer_h1,
                                    "estructura_completa": estructura_headings,
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
        """Retorna el script JavaScript para extraer TODA la estructura de headings"""
        return """
            () => {
                // Obtener TODOS los headings de la página
                const allHeadings = document.querySelectorAll('h1, h2, h3');
                
                if (allHeadings.length === 0) {
                    return { headings: [], total_h1: 0, total_h2: 0, total_h3: 0 };
                }
                
                // Convertir NodeList a Array y mapear la estructura
                const headingsArray = Array.from(allHeadings).map(heading => ({
                    tag: heading.tagName.toLowerCase(),
                    text: heading.textContent.trim(),
                    level: parseInt(heading.tagName.charAt(1))
                }));
                
                // Construir estructura jerárquica
                const result = {
                    headings: [],
                    total_h1: 0,
                    total_h2: 0,
                    total_h3: 0
                };
                
                let currentH1 = null;
                let currentH2 = null;
                
                headingsArray.forEach(heading => {
                    if (heading.tag === 'h1') {
                        currentH1 = {
                            titulo: heading.text,
                            level: 'h1',
                            h2: []
                        };
                        currentH2 = null;
                        result.headings.push(currentH1);
                        result.total_h1++;
                    } else if (heading.tag === 'h2') {
                        currentH2 = {
                            titulo: heading.text,
                            level: 'h2',
                            h3: []
                        };
                        
                        if (currentH1) {
                            currentH1.h2.push(currentH2);
                        } else {
                            // H2 sin H1 padre, crear estructura independiente
                            result.headings.push({
                                titulo: '[Sin H1]',
                                level: 'h1',
                                h2: [currentH2]
                            });
                        }
                        result.total_h2++;
                    } else if (heading.tag === 'h3') {
                        const h3Item = {
                            titulo: heading.text,
                            level: 'h3'
                        };
                        
                        if (currentH2) {
                            currentH2.h3.push(h3Item);
                        } else if (currentH1) {
                            // H3 sin H2 padre pero con H1
                            currentH2 = {
                                titulo: '[Sin H2]',
                                level: 'h2',
                                h3: [h3Item]
                            };
                            currentH1.h2.push(currentH2);
                        } else {
                            // H3 sin H1 ni H2 padre
                            result.headings.push({
                                titulo: '[Sin H1]',
                                level: 'h1',
                                h2: [{
                                    titulo: '[Sin H2]',
                                    level: 'h2',
                                    h3: [h3Item]
                                }]
                            });
                        }
                        result.total_h3++;
                    }
                });
                
                return result;
            }
        """
    
    def _extract_headings_from_soup(self, soup) -> Dict[str, Any]:
        """Extrae TODA la estructura de headings usando BeautifulSoup"""
        # Obtener TODOS los headings de la página
        all_headings = soup.find_all(['h1', 'h2', 'h3'])
        
        if not all_headings:
            return {"headings": [], "total_h1": 0, "total_h2": 0, "total_h3": 0}
        
        # Construir estructura jerárquica
        result = {
            "headings": [],
            "total_h1": 0,
            "total_h2": 0,
            "total_h3": 0
        }
        
        current_h1 = None
        current_h2 = None
        
        for heading in all_headings:
            tag_name = heading.name.lower()
            text = heading.get_text(strip=True)
            
            if tag_name == 'h1':
                current_h1 = {
                    "titulo": text,
                    "level": "h1",
                    "h2": []
                }
                current_h2 = None
                result["headings"].append(current_h1)
                result["total_h1"] += 1
                
            elif tag_name == 'h2':
                current_h2 = {
                    "titulo": text,
                    "level": "h2",
                    "h3": []
                }
                
                if current_h1:
                    current_h1["h2"].append(current_h2)
                else:
                    # H2 sin H1 padre, crear estructura independiente
                    result["headings"].append({
                        "titulo": "[Sin H1]",
                        "level": "h1",
                        "h2": [current_h2]
                    })
                result["total_h2"] += 1
                
            elif tag_name == 'h3':
                h3_item = {
                    "titulo": text,
                    "level": "h3"
                }
                
                if current_h2:
                    current_h2["h3"].append(h3_item)
                elif current_h1:
                    # H3 sin H2 padre pero con H1
                    current_h2 = {
                        "titulo": "[Sin H2]",
                        "level": "h2",
                        "h3": [h3_item]
                    }
                    current_h1["h2"].append(current_h2)
                else:
                    # H3 sin H1 ni H2 padre
                    result["headings"].append({
                        "titulo": "[Sin H1]",
                        "level": "h1",
                        "h2": [{
                            "titulo": "[Sin H2]",
                            "level": "h2",
                            "h3": [h3_item]
                        }]
                    })
                result["total_h3"] += 1
        
        return result
