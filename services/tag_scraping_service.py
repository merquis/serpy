import asyncio
import time
import random
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import httpx
from bs4 import BeautifulSoup
import logging
from config import config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio avanzado con medidas anti-bot para Booking y TripAdvisor"""

    def __init__(self):
        self.http_client = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        ]
        self.successful_httpx_count = 0
        self.playwright_fallback_count = 0

    async def scrape_tags_from_json(self, json_data: Any, max_concurrent: int = 5, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Procesa URLs con concurrencia muy limitada para evitar detección"""
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []

        # Headers mejorados para httpx
        headers = self._get_httpx_headers()

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers=headers,
            follow_redirects=True,
            http2=True,  # IMPORTANTE: Usar HTTP/2
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        ) as http_client:
            self.http_client = http_client

            async with async_playwright() as p:
                # Usar Firefox en lugar de Chrome para mejor evasión
                # Volver a Chrome con la configuración que funciona
                browser = await p.chromium.launch(
                    headless=True,  # Puede funcionar con los args correctos
                    args=[
                        "--disable-blink-features=AutomationControlled",  # CRÍTICO
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--window-size=1920,1080",
                        "--start-maximized",
                        "--disable-gpu",
                        "--disable-dev-tools",
                        "--disable-extensions",
                        "--disable-images"  # Opcional: más rápido sin imágenes
                    ]
                )
                try:
                    for item in data_list:
                        if not isinstance(item, dict):
                            continue

                        context = {
                            "busqueda": item.get("busqueda", ""),
                            "idioma": item.get("idioma", ""),
                            "region": item.get("region", ""),
                            "dominio": item.get("dominio", ""),
                            "url_busqueda": item.get("url_busqueda", "")
                        }

                        urls = self._extract_urls_from_item(item)
                        if urls:
                            results = await self._process_urls_concurrent(urls, browser, max_concurrent, progress_callback)
                            all_results.append({**context, "resultados": results})
                            
                    logger.info(f"Scraping completado - httpx: {self.successful_httpx_count}, Playwright: {self.playwright_fallback_count}")
                    
                finally:
                    await browser.close()
                    self.http_client = None

        return all_results

    def _get_httpx_headers(self) -> Dict[str, str]:
        """Headers optimizados para httpx"""
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Pragma": "no-cache"
        }

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        urls = []
        if "urls" in item:
            for url_item in item["urls"]:
                if isinstance(url_item, str):
                    urls.append(url_item)
                elif isinstance(url_item, dict) and "url" in url_item:
                    urls.append(url_item["url"])
        if "resultados" in item:
            for result in item["resultados"]:
                if isinstance(result, dict) and "url" in result:
                    urls.append(result["url"])
        return urls

    async def _process_urls_concurrent(self, urls: List[str], browser: Browser, max_concurrent: int, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Procesa URLs concurrentemente pero mantiene el orden original"""
        results = [None] * len(urls)  # Pre-allocate para mantener orden
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0

        async def process_single_url(index: int, url: str):
            """Procesa una URL manteniendo su índice original"""
            nonlocal completed_count
            async with semaphore:
                try:
                    if progress_callback:
                        progress_callback(f"🔄 Procesando {index+1}/{len(urls)}: {url[:50]}...")
                    
                    # Delay aleatorio corto entre requests
                    if completed_count > 0:
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                    
                    result = await self._scrape_single_url(url, browser)
                    results[index] = result  # Guardar en posición original
                    completed_count += 1
                    
                    if progress_callback:
                        method = result.get("method", "unknown")
                        progress_callback(f"✅ Completadas: {completed_count}/{len(urls)} | Método: {method}")
                        
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    results[index] = {"url": url, "status_code": "error", "error": str(e)}
                    completed_count += 1

        # Crear tareas con índices para mantener orden
        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        return results

    async def _scrape_single_url(self, url: str, browser: Browser) -> Dict[str, Any]:
        """Intenta con httpx primero, luego Playwright si falla"""
        start_time = time.time()
        
        # Intentar primero con httpx para TODOS los sitios
        try:
            self.http_client.headers["User-Agent"] = random.choice(self.user_agents)
            response = await self.http_client.get(url)
            
            if response.status_code == 200 and len(response.content) > 1000:
                result = await self._scrape_with_httpx(url, response, start_time)
                if result["h1"]:
                    self.successful_httpx_count += 1
                    return result
                else:
                    logger.info(f"No h1 found with httpx for {url}, falling back to Playwright")
            else:
                logger.info(f"httpx returned status {response.status_code} for {url}, falling back to Playwright")
                
        except Exception as e:
            logger.warning(f"httpx failed for {url}: {e}, falling back to Playwright")
        
        # Fallback a Playwright
        self.playwright_fallback_count += 1
        return await self._scrape_with_playwright(url, browser, start_time)

    async def _scrape_with_httpx(self, url: str, response: httpx.Response, start_time: float) -> Dict[str, Any]:
        """Procesa respuesta de httpx"""
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
            
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else ""
        h1_structure = self._extract_heading_structure_soup(soup)
        elapsed_time = time.time() - start_time
        
        logger.info(f"Scraped {url} with httpx in {elapsed_time:.2f}s")
        
        return {
            "url": url,
            "status_code": response.status_code,
            "title": title,
            "h1": h1_structure,
            "scraping_time": elapsed_time,
            "method": "httpx"
        }

    async def _scrape_with_playwright(self, url: str, browser: Browser, start_time: float) -> Dict[str, Any]:
        """Scraping avanzado con Playwright y máximas medidas anti-detección"""
        context = None
        page = None
        
        try:
            # Crear contexto con configuración máxima anti-detección
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(self.user_agents),
                locale="es-ES",
                timezone_id="Europe/Madrid",
                ignore_https_errors=True,
                java_script_enabled=True,
                has_touch=False,
                is_mobile=False,
                device_scale_factor=1,
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1"
                }
            )
            
            page = await context.new_page()
            
            
            # Scripts anti-detección más agresivos
            await page.add_init_script("""
                // Eliminar todas las propiedades que delatan automatización
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });
                
                // Chrome sin headless
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format", 
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        }
                    ]
                });
                
                // Modificar permisos
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // WebGL vendor
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };
                
                // Languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en-US', 'en']
                });
                
                // Platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                
                // Hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });
                
                // Device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
            """)
            
            # Configurar timeouts largos
            page.set_default_timeout(60000)
            
            # Navegar a la URL
            response = await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Esperar un poco para que cargue el contenido
            await page.wait_for_timeout(random.randint(2000, 4000))
            
            # Pequeño scroll para trigger lazy loading
            await page.evaluate("window.scrollBy(0, 300)")
            await page.wait_for_timeout(1000)
            
            # Intentar esperar h1 con más tiempo
            try:
                await page.wait_for_selector("h1", timeout=10000)
            except:
                # Si no encuentra h1, buscar alternativas
                logger.warning(f"No h1 found immediately for {url}, searching alternatives...")
            
            # Extraer datos
            title = await page.title()
            h1_structure = await self._extract_heading_structure_playwright(page)
            
            # Si no encontramos h1, intentar con selectores específicos
            if not h1_structure:
                h1_structure = await self._extract_heading_structure_alternative(page)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Scraped {url} with Playwright in {elapsed_time:.2f}s")
            
            
            return {
                "url": url,
                "status_code": 200,  # Asumimos 200 si llegamos aquí
                "title": title,
                "h1": h1_structure,
                "scraping_time": elapsed_time,
                "method": "playwright_advanced"
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error scraping {url} after {elapsed_time:.2f}s: {e}")
            return {
                "url": url,
                "status_code": "error",
                "error": str(e),
                "scraping_time": elapsed_time,
                "method": "playwright_failed"
            }
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass

    async def _extract_heading_structure_alternative(self, page: Page) -> Dict[str, Any]:
        """Busca h1 con selectores alternativos para sitios específicos"""
        return await page.evaluate("""
            () => {
                // Selectores específicos para Booking y TripAdvisor
                const selectors = [
                    'h1',
                    '[data-testid="header-title"]',
                    '.hp__hotel-name',
                    '#HEADING',
                    '.heading_title',
                    '.property-title',
                    '[class*="hotel-name"]',
                    '[class*="property-name"]'
                ];
                
                let h1 = null;
                for (const selector of selectors) {
                    h1 = document.querySelector(selector);
                    if (h1) break;
                }
                
                if (!h1) return {};
                
                const result = { 
                    titulo: h1.textContent.trim(), 
                    level: 'h1', 
                    h2: [] 
                };
                
                // Buscar h2s relacionados
                const h2s = document.querySelectorAll('h2');
                h2s.forEach(h2 => {
                    if (h2.textContent.trim()) {
                        result.h2.push({
                            titulo: h2.textContent.trim(),
                            level: 'h2',
                            h3: []
                        });
                    }
                });
                
                return result;
            }
        """)

    def _extract_heading_structure_soup(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae estructura de encabezados con BeautifulSoup"""
        h1 = soup.find('h1')
        if not h1:
            return {}
            
        result = {"titulo": h1.text.strip(), "level": "h1", "h2": []}
        current = h1.find_next_sibling()
        current_h2 = None
        
        while current:
            if current.name == 'h1':
                break
            elif current.name == 'h2':
                current_h2 = {"titulo": current.text.strip(), "level": "h2", "h3": []}
                result["h2"].append(current_h2)
            elif current.name == 'h3' and current_h2:
                current_h2["h3"].append({"titulo": current.text.strip(), "level": "h3"})
            current = current.find_next_sibling()
            
        return result

    async def _extract_heading_structure_playwright(self, page: Page) -> Dict[str, Any]:
        """Extrae estructura de encabezados con Playwright"""
        return await page.evaluate("""
            () => {
                const h1 = document.querySelector('h1');
                if (!h1) return {};
                
                const result = { 
                    titulo: h1.textContent.trim(), 
                    level: 'h1', 
                    h2: [] 
                };
                
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
