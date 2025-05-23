"""
Servicio de Tag Scraping - Extracción de estructura HTML
"""
import asyncio
import time
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser
import logging
from config import config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""
    
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
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            try:
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
                        # Procesar URLs con concurrencia limitada
                        results = await self._process_urls_concurrent(
                            urls, 
                            browser, 
                            max_concurrent,
                            progress_callback
                        )
                        
                        all_results.append({
                            **context,
                            "resultados": results
                        })
                
            finally:
                await browser.close()
        
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
    
    async def _process_urls_concurrent(
        self,
        urls: List[str],
        browser: Browser,
        max_concurrent: int,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Procesa múltiples URLs con límite de concurrencia"""
        results = [None] * len(urls)
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0
        active_tasks = set()
        
        async def process_single_url(index: int, url: str):
            async with semaphore:
                try:
                    # Agregar a tareas activas
                    active_tasks.add(url)
                    
                    if progress_callback:
                        progress_callback(
                            f"🔄 Procesando {len(active_tasks)}/{max_concurrent} tareas concurrentes | "
                            f"Completadas: {completed_count}/{len(urls)} | "
                            f"Actual: {url[:50]}..."
                        )
                    
                    result = await self._scrape_single_url(url, browser)
                    results[index] = result
                    
                    # Actualizar contador de completadas
                    nonlocal completed_count
                    completed_count += 1
                    
                    # Remover de tareas activas
                    active_tasks.discard(url)
                    
                    if progress_callback:
                        progress_callback(
                            f"✅ Completadas: {completed_count}/{len(urls)} | "
                            f"Activas: {len(active_tasks)} | "
                            f"URL: {url[:50]}..."
                        )
                    
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    results[index] = {
                        "url": url,
                        "status_code": "error",
                        "error": str(e)
                    }
                    
                    # Actualizar contador incluso en error
                    nonlocal completed_count
                    completed_count += 1
                    active_tasks.discard(url)
        
        # Crear tareas para todas las URLs
        tasks = [
            process_single_url(i, url) 
            for i, url in enumerate(urls)
        ]
        
        # Ejecutar todas las tareas
        await asyncio.gather(*tasks)
        
        return results
    
    async def _scrape_single_url(
        self, 
        url: str, 
        browser: Browser
    ) -> Dict[str, Any]:
        """Extrae la estructura de etiquetas de una URL"""
        page = await browser.new_page()
        start_time = time.time()
        
        try:
            # Configurar timeout más corto para acelerar procesamiento
            page.set_default_timeout(20000)  # 20 segundos
            
            # Navegar a la URL
            response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            status_code = response.status if response else 0
            
            # Esperar un poco para que se cargue el contenido dinámico
            await page.wait_for_timeout(1000)
            
            # Extraer título
            title = await page.title()
            
            # Extraer estructura H1 -> H2 -> H3
            h1_structure = await self._extract_heading_structure(page)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Scraped {url} in {elapsed_time:.2f}s")
            
            return {
                "url": url,
                "status_code": status_code,
                "title": title,
                "h1": h1_structure,
                "scraping_time": elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error scraping {url} after {elapsed_time:.2f}s: {e}")
            raise
        finally:
            await page.close()
    
    async def _extract_heading_structure(self, page) -> Dict[str, Any]:
        """Extrae la estructura jerárquica de headings"""
        # Ejecutar JavaScript para extraer la estructura
        structure = await page.evaluate("""
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
        """)
        
        return structure 