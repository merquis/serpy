import asyncio
import time
import random
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
import httpx
from bs4 import BeautifulSoup
import logging
from config import config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio optimizado para extraer estructura jerárquica de etiquetas HTML
    Estrategia: httpx primero (rápido) -> Playwright si falla (robusto)"""

    def __init__(self):
        self.http_client = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]
        self.successful_httpx_count = 0
        self.playwright_fallback_count = 0

    async def scrape_tags_from_json(self, json_data: Any, max_concurrent: int = 5, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Procesa URLs manteniendo el orden original"""
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []

        # Headers mejorados para httpx
        headers = {
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

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers=headers,
            follow_redirects=True,
            http2=True,  # Usar HTTP/2
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        ) as http_client:
            self.http_client = http_client

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,  # Cambiar a False si hay muchos bloqueos
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--window-size=1920,1080",
                        "--start-maximized"
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
                            
                    # Log estadísticas
                    logger.info(f"Scraping completado - httpx exitosos: {self.successful_httpx_count}, Playwright fallbacks: {self.playwright_fallback_count}")
                    
                finally:
                    await browser.close()
                    self.http_client = None

        return all_results

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        """Extrae URLs manteniendo el orden original"""
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
        active_tasks = set()

        async def process_single_url(index: int, url: str):
            """Procesa una URL manteniendo su índice original"""
            nonlocal completed_count
            async with semaphore:
                try:
                    active_tasks.add(url)
                    if progress_callback:
                        progress_callback(f"🔄 Procesando {len(active_tasks)}/{max_concurrent} tareas | Completadas: {completed_count}/{len(urls)} | URL: {url[:50]}...")
                    
                    # Delay aleatorio entre requests para evitar rate limiting
                    if completed_count > 0:
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                    
                    result = await self._scrape_single_url(url, browser)
                    results[index] = result  # Guardar en posición original
                    completed_count += 1
                    active_tasks.discard(url)
                    
                    if progress_callback:
                        method = result.get("method", "unknown")
                        progress_callback(f"✅ Completadas: {completed_count}/{len(urls)} | Método: {method} | URL: {url[:50]}...")
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    results[index] = {"url": url, "status_code": "error", "error": str(e)}
                    completed_count += 1
                    active_tasks.discard(url)

        # Crear tareas con índices para mantener orden
        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        return results

    async def _scrape_single_url(self, url: str, browser: Browser) -> Dict[str, Any]:
        """Intenta primero con httpx, luego con Playwright si falla"""
        start_time = time.time()
        
        # Intentar primero con httpx
        try:
            # Cambiar User-Agent para cada request
            self.http_client.headers["User-Agent"] = random.choice(self.user_agents)
            
            response = await self.http_client.get(url)
            
            # Si respuesta exitosa y tiene contenido
            if response.status_code == 200 and len(response.content) > 1000:
                result = await self._scrape_with_httpx(url, response, start_time)
                
                # Verificar que encontramos h1
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
        
        # Eliminar scripts y estilos para un parsing más limpio
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

    def _extract_heading_structure_soup(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae estructura de encabezados con BeautifulSoup"""
        h1 = soup.find('h1')
        if not h1:
            return {}
            
        result = {"titulo": h1.text.strip(), "level": "h1", "h2": []}
        
        # Buscar hermanos siguientes hasta el próximo h1
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

    async def _scrape_with_playwright(self, url: str, browser: Browser, start_time: float) -> Dict[str, Any]:
        """Scraping robusto con Playwright cuando httpx falla"""
        context = None
        page = None
        
        try:
            # Contexto con configuración anti-detección
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(self.user_agents),
                locale="es-ES",
                timezone_id="Europe/Madrid",
                ignore_https_errors=True,
                java_script_enabled=True,
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1"
                }
            )
            
            page = await context.new_page()
            
            # Inyectar scripts anti-detección
            await page.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override chrome
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5].map((n) => ({
                        name: `Chrome PDF Plugin ${n}`,
                        description: 'Portable Document Format',
                        filename: 'internal-pdf-viewer',
                        length: 1
                    }))
                });
            """)
            
            # Configurar timeouts
            page.set_default_timeout(45000)
            
            # Navegar
            response = await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Esperar contenido
            await page.wait_for_timeout(random.randint(1500, 3000))
            
            # Intentar esperar h1
            try:
                await page.wait_for_selector("h1", timeout=5000)
            except:
                pass
            
            # Pequeño scroll para cargar lazy content
            await page.evaluate("window.scrollTo(0, 500)")
            await page.wait_for_timeout(500)
            await page.evaluate("window.scrollTo(0, 0)")
            
            # Extraer datos
            title = await page.title()
            h1_structure = await self._extract_heading_structure_playwright(page)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Scraped {url} with Playwright in {elapsed_time:.2f}s")
            
            return {
                "url": url,
                "status_code": response.status if response else 200,
                "title": title,
                "h1": h1_structure,
                "scraping_time": elapsed_time,
                "method": "playwright"
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error scraping {url} with Playwright after {elapsed_time:.2f}s: {e}")
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
