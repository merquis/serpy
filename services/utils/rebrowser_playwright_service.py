"""
Servicio de Rebrowser Playwright para evitar detección de bots
Usa rebrowser-playwright que ya incluye parches anti-detección
"""
import asyncio
from typing import List, Dict, Optional, Tuple, Any, Callable
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import logging
import random

logger = logging.getLogger(__name__)


class RebrowserConfig:
    """Configuración optimizada para evitar detección de bots con rebrowser-playwright"""
    def __init__(
        self,
        headless: bool = False,  # Mejor detección en modo no-headless
        timeout: int = 60000,
        wait_until: str = "networkidle",
        user_agent: Optional[str] = None,
        accept_language: str = "es-ES,es;q=0.9,en;q=0.8",
        ignore_https_errors: bool = True,
        wait_for_selector: Optional[str] = None,
        wait_for_timeout: int = 15000,
        extra_headers: Optional[Dict[str, str]] = None,
        browser_args: Optional[List[str]] = None,
        viewport: Optional[Dict[str, int]] = None,
        locale: str = "es-ES",
        timezone: str = "Europe/Madrid",
        geolocation: Optional[Dict[str, float]] = None,
        permissions: Optional[List[str]] = None,
        color_scheme: str = "light",
        device_scale_factor: float = 1.0,
        is_mobile: bool = False,
        has_touch: bool = False,
        default_browser_type: str = "chromium"  # chromium, firefox, webkit
    ):
        self.headless = headless
        self.timeout = timeout
        self.wait_until = wait_until
        self.user_agent = user_agent or self._get_random_user_agent()
        self.accept_language = accept_language
        self.ignore_https_errors = ignore_https_errors
        self.wait_for_selector = wait_for_selector
        self.wait_for_timeout = wait_for_timeout
        self.extra_headers = extra_headers or {}
        self.browser_args = browser_args or self._get_optimized_browser_args()
        self.viewport = viewport or {"width": 1920, "height": 1080}
        self.locale = locale
        self.timezone = timezone
        self.geolocation = geolocation
        self.permissions = permissions or []
        self.color_scheme = color_scheme
        self.device_scale_factor = device_scale_factor
        self.is_mobile = is_mobile
        self.has_touch = has_touch
        self.default_browser_type = default_browser_type
    
    def _get_random_user_agent(self) -> str:
        """Obtiene un user agent aleatorio realista"""
        user_agents = [
            # Chrome Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            # Chrome Mac
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            # Chrome Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            # Firefox
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
            # Safari
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
            # Edge
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        ]
        return random.choice(user_agents)
    
    def _get_optimized_browser_args(self) -> List[str]:
        """Obtiene argumentos optimizados para rebrowser-playwright"""
        # Argumentos básicos que funcionan bien con rebrowser-playwright
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",  # Importante para anti-detección
            "--window-size=1920,1080",
            "--start-maximized"
        ]
        
        # Argumentos adicionales para mejorar el rendimiento
        performance_args = [
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection"
        ]
        
        return args + performance_args


class RebrowserPlaywrightService:
    """Servicio para scraping con rebrowser-playwright evitando detección de bots"""
    
    def __init__(self, config: Optional[RebrowserConfig] = None):
        self.config = config or RebrowserConfig()
    
    async def _create_context(self, browser: Browser) -> BrowserContext:
        """Crea un contexto de navegador con configuración anti-detección"""
        context_options = {
            "viewport": self.config.viewport,
            "user_agent": self.config.user_agent,
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
            "ignore_https_errors": self.config.ignore_https_errors,
            "color_scheme": self.config.color_scheme,
            "device_scale_factor": self.config.device_scale_factor,
            "is_mobile": self.config.is_mobile,
            "has_touch": self.config.has_touch,
            "extra_http_headers": {
                "Accept-Language": self.config.accept_language,
                **self.config.extra_headers
            }
        }
        
        # Añadir geolocalización si está configurada
        if self.config.geolocation:
            context_options["geolocation"] = self.config.geolocation
            context_options["permissions"] = ["geolocation"] + self.config.permissions
        elif self.config.permissions:
            context_options["permissions"] = self.config.permissions
        
        context = await browser.new_context(**context_options)
        
        # Añadir scripts de inicialización para mejorar el stealth
        await context.add_init_script("""
            // Añadir variación aleatoria en el comportamiento del mouse
            const originalMoveTo = MouseEvent.prototype.moveTo;
            if (originalMoveTo) {
                MouseEvent.prototype.moveTo = function(...args) {
                    // Añadir pequeña variación aleatoria
                    if (args[0] && typeof args[0] === 'number') {
                        args[0] += (Math.random() - 0.5) * 2;
                    }
                    if (args[1] && typeof args[1] === 'number') {
                        args[1] += (Math.random() - 0.5) * 2;
                    }
                    return originalMoveTo.apply(this, args);
                };
            }
            
            // Simular comportamiento de batería más realista
            if ('getBattery' in navigator) {
                navigator.getBattery = async () => ({
                    charging: Math.random() > 0.5,
                    chargingTime: Math.random() > 0.5 ? 0 : Math.floor(Math.random() * 3600),
                    dischargingTime: Math.random() > 0.5 ? Infinity : Math.floor(Math.random() * 10800),
                    level: 0.5 + Math.random() * 0.5
                });
            }
        """)
        
        return context
    
    async def get_html(
        self,
        url: str,
        browser_instance: Browser,
        config: Optional[RebrowserConfig] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Obtiene el HTML de una URL usando rebrowser-playwright.
        
        Args:
            url: URL a scrapear
            browser_instance: Instancia del navegador
            config: Configuración opcional
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        html = ""
        context = None
        page = None
        
        try:
            # Crear contexto con configuración anti-detección
            context = await self._create_context(browser_instance)
            
            # Crear nueva página
            page = await context.new_page()
            
            # Añadir delay aleatorio antes de navegar (comportamiento humano)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Navegar a la URL
            response = await page.goto(
                url,
                timeout=config.timeout,
                wait_until=config.wait_until
            )
            
            status_code = response.status if response else 0
            
            # Esperar un poco para que la página se cargue completamente
            await asyncio.sleep(random.uniform(1, 2))
            
            # Simular scroll aleatorio (comportamiento humano)
            await self._simulate_human_scroll(page)
            
            # Esperar selector específico si se proporciona
            if config.wait_for_selector:
                await page.wait_for_selector(
                    config.wait_for_selector,
                    timeout=config.wait_for_timeout
                )
            
            # Obtener el HTML
            html = await page.content()
            
            if not html:
                return {
                    "error": "HTML_Vacio",
                    "url": url,
                    "status_code": status_code,
                    "details": "No se obtuvo contenido HTML."
                }, ""
            
            # Retornar éxito
            return {
                "success": True,
                "url": url,
                "status_code": status_code,
                "html_length": len(html)
            }, html
            
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout al cargar {url}: {e}")
            return {
                "error": "Timeout_Rebrowser",
                "url": url,
                "details": f"Timeout al cargar la página: {str(e)}"
            }, ""
            
        except Exception as e:
            logger.error(f"Error al obtener HTML de {url}: {e}")
            error_type = type(e).__name__
            return {
                "error": f"Excepcion_Rebrowser_{error_type}",
                "url": url,
                "details": str(e)
            }, ""
            
        finally:
            # Cerrar página y contexto
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
    
    async def _simulate_human_scroll(self, page: Page) -> None:
        """Simula scroll humano en la página"""
        try:
            # Obtener altura de la página
            scroll_height = await page.evaluate("document.body.scrollHeight")
            viewport_height = await page.evaluate("window.innerHeight")
            
            if scroll_height > viewport_height:
                # Hacer 2-3 scrolls aleatorios
                num_scrolls = random.randint(2, 3)
                for _ in range(num_scrolls):
                    # Scroll aleatorio entre 20% y 80% de la viewport
                    scroll_amount = random.randint(
                        int(viewport_height * 0.2),
                        int(viewport_height * 0.8)
                    )
                    
                    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Volver arriba ocasionalmente
                if random.random() > 0.7:
                    await page.evaluate("window.scrollTo(0, 0)")
                    await asyncio.sleep(random.uniform(0.3, 0.7))
                    
        except Exception as e:
            logger.debug(f"Error en simulación de scroll: {e}")
    
    async def process_urls_batch(
        self,
        urls: List[str],
        process_func: Callable,
        config: Optional[RebrowserConfig] = None,
        max_concurrent: int = 3,  # Reducido para parecer más humano
        progress_callback: Optional[Callable] = None,
        delay_between_requests: Tuple[float, float] = (2.0, 5.0)  # Delay entre requests
    ) -> List[Any]:
        """
        Procesa múltiples URLs en lote con rebrowser-playwright.
        
        Args:
            urls: Lista de URLs a procesar
            process_func: Función para procesar cada resultado
            config: Configuración opcional
            max_concurrent: Número máximo de páginas concurrentes
            progress_callback: Callback para reportar progreso
            delay_between_requests: Tupla (min, max) de segundos de delay entre requests
            
        Returns:
            Lista de resultados procesados
        """
        config = config or self.config
        results = []
        
        async with async_playwright() as p:
            # Seleccionar el tipo de navegador
            browser_type = getattr(p, config.default_browser_type)
            
            # Lanzar navegador con configuración anti-detección
            browser = await browser_type.launch(
                headless=config.headless,
                args=config.browser_args
            )
            
            try:
                # Semáforo para limitar concurrencia
                semaphore = asyncio.Semaphore(max_concurrent)
                
                # Tracking de URLs activas
                active_urls = set()
                completed_count = 0
                
                async def process_single_url(index: int, url: str):
                    nonlocal completed_count
                    
                    async with semaphore:
                        try:
                            # Delay aleatorio entre requests
                            if index > 0:
                                delay = random.uniform(*delay_between_requests)
                                await asyncio.sleep(delay)
                            
                            # Agregar a URLs activas
                            active_urls.add(url)
                            
                            if progress_callback:
                                progress_info = {
                                    "message": f"Procesando {index+1}/{len(urls)}: {url}",
                                    "current_url": url,
                                    "active_urls": list(active_urls),
                                    "completed": completed_count,
                                    "total": len(urls),
                                    "remaining": len(urls) - completed_count
                                }
                                progress_callback(progress_info)
                            
                            # Obtener HTML
                            result_dict, html = await self.get_html(url, browser, config)
                            
                            # Procesar con la función proporcionada
                            if result_dict.get("success") and html:
                                processed_result = await process_func(url, html, browser)
                                return processed_result
                            else:
                                return result_dict
                                
                        except Exception as e:
                            logger.error(f"Error procesando {url}: {e}")
                            return {
                                "error": "Error_Procesamiento",
                                "url": url,
                                "details": str(e)
                            }
                        finally:
                            # Remover de URLs activas y actualizar contador
                            active_urls.discard(url)
                            completed_count += 1
                
                # Crear tareas para todas las URLs
                tasks = [
                    process_single_url(i, url)
                    for i, url in enumerate(urls)
                ]
                
                # Ejecutar todas las tareas
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar excepciones
                final_results = []
                for i, res in enumerate(results):
                    if isinstance(res, Exception):
                        final_results.append({
                            "error": "Excepcion_Gather",
                            "url": urls[i],
                            "details": str(res)
                        })
                    else:
                        final_results.append(res)
                
                return final_results
                
            finally:
                await browser.close()
    
    async def get_html_simple(
        self,
        url: str,
        config: Optional[RebrowserConfig] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Función simplificada para obtener HTML de una sola URL.
        
        Args:
            url: URL a scrapear
            config: Configuración opcional
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        
        async with async_playwright() as p:
            browser_type = getattr(p, config.default_browser_type)
            browser = await browser_type.launch(
                headless=config.headless,
                args=config.browser_args
            )
            try:
                result = await self.get_html(url, browser, config)
                return result
            finally:
                await browser.close()
    
    async def execute_javascript(
        self,
        page: Page,
        script: str
    ) -> Any:
        """
        Ejecuta JavaScript en la página y retorna el resultado.
        
        Args:
            page: Instancia de la página
            script: Código JavaScript a ejecutar
            
        Returns:
            Resultado de la ejecución del script
        """
        try:
            return await page.evaluate(script)
        except Exception as e:
            logger.error(f"Error ejecutando JavaScript: {e}")
            raise


# Funciones helper para configuraciones comunes

def create_stealth_config(
    headless: bool = False,
    browser_type: str = "chromium"
) -> RebrowserConfig:
    """Crea una configuración optimizada para máximo stealth"""
    return RebrowserConfig(
        headless=headless,
        default_browser_type=browser_type,
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=1.0
    )


def create_mobile_config(
    device: str = "iPhone 13"
) -> RebrowserConfig:
    """Crea una configuración para emular dispositivo móvil"""
    mobile_configs = {
        "iPhone 13": {
            "viewport": {"width": 390, "height": 844},
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "device_scale_factor": 3.0,
            "is_mobile": True,
            "has_touch": True
        },
        "Samsung Galaxy S21": {
            "viewport": {"width": 360, "height": 800},
            "user_agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
            "device_scale_factor": 2.625,
            "is_mobile": True,
            "has_touch": True
        }
    }
    
    config_data = mobile_configs.get(device, mobile_configs["iPhone 13"])
    
    return RebrowserConfig(
        headless=False,
        viewport=config_data["viewport"],
        user_agent=config_data["user_agent"],
        device_scale_factor=config_data["device_scale_factor"],
        is_mobile=config_data["is_mobile"],
        has_touch=config_data["has_touch"]
    )


def create_fast_stealth_config() -> RebrowserConfig:
    """Crea una configuración rápida pero con anti-detección"""
    return RebrowserConfig(
        wait_until="domcontentloaded",
        timeout=30000,
        wait_for_timeout=5000,
        headless=True  # Más rápido en headless
    )


# Ejemplo de uso
async def example_usage():
    """Ejemplo de cómo usar el servicio rebrowser-playwright"""
    # Crear servicio con configuración stealth
    service = RebrowserPlaywrightService(create_stealth_config())
    
    # Obtener HTML de una sola página
    result, html = await service.get_html_simple("https://example.com")
    
    if result.get("success"):
        print(f"HTML obtenido: {len(html)} caracteres")
    else:
        print(f"Error: {result}")
    
    # Procesar múltiples URLs
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net"
    ]
    
    async def process_html(url: str, html: str, browser: Browser) -> Dict[str, Any]:
        # Procesar el HTML como necesites
        return {
            "url": url,
            "title": html[html.find("<title>"):html.find("</title>")],
            "length": len(html)
        }
    
    results = await service.process_urls_batch(
        urls,
        process_html,
        max_concurrent=2,
        delay_between_requests=(3.0, 6.0)  # Delay más humano
    )
    
    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(example_usage())
