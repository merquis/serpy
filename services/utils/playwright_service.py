"""
Servicio base de Playwright para scraping reutilizable
Proporciona funcionalidad común para todos los servicios de scraping
"""
import asyncio
import random
from typing import List, Dict, Optional, Tuple, Any, Callable
from rebrowser_playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import logging

logger = logging.getLogger(__name__)


from services.utils.anti_bot_utils import get_realistic_headers, rotate_headers

class PlaywrightConfig:
    """Configuración para las solicitudes de Playwright
    
    rebrowser-playwright maneja automáticamente:
    - User agents realistas
    - Accept-Language headers
    - Fingerprinting evasion
    - WebDriver detection bypass
    - Otros headers y configuraciones anti-bot
    """
    def __init__(
        self,
        headless: bool = True,              # Si ejecutar sin interfaz gráfica
        timeout: int = 30000,               # Timeout para cargar páginas (ms) - Reducido de 60s a 30s
        wait_until: str = "domcontentloaded",    # Cambiado de "networkidle" para mayor velocidad
        ignore_https_errors: bool = True,   # Ignorar errores SSL
        wait_for_selector: Optional[str] = None,     # Selector CSS a esperar
        wait_for_timeout: int = 10000,      # Timeout para esperar selector (ms) - Reducido de 15s a 10s
        extra_headers: Optional[Dict[str, str]] = None,  # Headers adicionales personalizados
        browser_args: Optional[List[str]] = None,   # Argumentos adicionales del navegador
        viewport: Optional[Dict[str, int]] = None,
        locale: str = "es-ES",
        timezone_id: str = "Europe/Madrid",
        block_resources: bool = True,
        max_retries: int = 2,               # Número de reintentos en caso de fallo
        retry_delay: float = 2.0,           # Delay base entre reintentos (exponencial)
        human_delay_range: Tuple[float, float] = (1.0, 3.0),  # Rango de delay humano entre acciones
        validate_content: bool = False      # Desactivado por defecto para evitar falsos positivos
    ):
        self.headless = headless
        self.timeout = timeout
        self.wait_until = wait_until
        self.ignore_https_errors = ignore_https_errors
        self.wait_for_selector = wait_for_selector
        self.wait_for_timeout = wait_for_timeout
        self.extra_headers = extra_headers or rotate_headers()
        self.browser_args = browser_args or [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-sandbox"
        ]
        self.viewport = viewport or {"width": 1920, "height": 1080}  # Viewport más realista
        self.locale = locale
        self.timezone_id = timezone_id
        self.block_resources = block_resources
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.human_delay_range = human_delay_range
        self.validate_content = validate_content


class PlaywrightService:
    """Servicio base para operaciones con Playwright"""
    
    def __init__(self, config: Optional[PlaywrightConfig] = None):
        self.config = config or PlaywrightConfig()
    
    async def _validate_content(self, html: str, url: str) -> bool:
        """
        Valida que el contenido HTML sea válido y no sea una página de error/bloqueo
        """
        if not html:
            logger.warning(f"HTML vacío para {url}")
            return False
            
        # Reducir el mínimo de caracteres requeridos
        if len(html) < 500:  # Reducido de 1000 a 500
            logger.warning(f"Contenido muy corto para {url}: {len(html)} caracteres")
            return False
        
        # Verificar indicadores de bloqueo comunes
        lower_html = html.lower()
        blocked_indicators = [
            'access denied', 'forbidden',
            'captcha', 'recaptcha', 'hcaptcha',
            'cloudflare', 'cf-ray',
            'please enable javascript',
            'checking your browser'
        ]
        
        # No incluir "blocked" como indicador porque puede aparecer en contenido legítimo
        for indicator in blocked_indicators:
            if indicator in lower_html:
                logger.warning(f"Indicador de bloqueo encontrado en {url}: {indicator}")
                return False
        
        # Verificar que haya contenido real - ser menos estricto
        # Buscar cualquier etiqueta de contenido, no solo headers
        content_tags = ['<h1', '<h2', '<h3', '<p', '<div', '<article', '<section', '<main']
        if not any(tag in lower_html for tag in content_tags):
            logger.warning(f"No se encontró contenido estructurado en {url}")
            return False
        
        # Si llegamos aquí, el contenido parece válido
        logger.debug(f"Contenido válido para {url}: {len(html)} caracteres")
        return True
    
    async def _human_like_behavior(self, page: Page):
        """
        Simula comportamiento humano en la página
        """
        try:
            # Delay aleatorio
            delay = random.uniform(*self.config.human_delay_range)
            await asyncio.sleep(delay)
            
            # Movimiento de mouse aleatorio
            width = self.config.viewport["width"]
            height = self.config.viewport["height"]
            
            # 2-3 movimientos aleatorios
            for _ in range(random.randint(2, 3)):
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Scroll aleatorio pequeño
            scroll_y = random.randint(100, 300)
            await page.evaluate(f"window.scrollBy(0, {scroll_y})")
            
        except Exception as e:
            logger.debug(f"Error en comportamiento humano (no crítico): {e}")
    
    async def get_html(
        self,
        url: str,
        browser_instance: Browser,
        config: Optional[PlaywrightConfig] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Obtiene el HTML de una URL usando Playwright con reintentos y optimizaciones.
        
        Args:
            url: URL a scrapear
            browser_instance: Instancia del navegador Playwright
            config: Configuración opcional de Playwright
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        
        for attempt in range(config.max_retries):
            context = None
            page = None
            
            try:
                # Crear un nuevo contexto para cada página (más seguro)
                context = await browser_instance.new_context(
                    ignore_https_errors=config.ignore_https_errors,
                    viewport=config.viewport,
                    locale=config.locale,
                    timezone_id=config.timezone_id,
                    extra_http_headers=rotate_headers()  # Rotar headers para cada página
                )
                
                # Crear nueva página
                page = await context.new_page()
                
                # Configurar timeouts específicos
                page.set_default_timeout(config.timeout)
                page.set_default_navigation_timeout(config.timeout)
                
                # Bloquear recursos innecesarios si está activado
                if config.block_resources:
                    async def block_route(route, request):
                        # No bloquear CSS - puede ser necesario para renderizado
                        if request.resource_type in ["image", "font", "media"]:
                            await route.abort()
                        elif any(request.url.lower().endswith(ext) for ext in [
                            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", 
                            ".woff", ".woff2", ".ttf", ".eot", 
                            ".mp4", ".webm", ".avi", ".mov"
                        ]):
                            await route.abort()
                        else:
                            await route.continue_()
                    
                    await page.route("**/*", block_route)
                
                # Navegar a la URL
                response = await page.goto(
                    url,
                    timeout=config.timeout,
                    wait_until=config.wait_until
                )
                
                status_code = response.status if response else 0
                
                # Comportamiento humano
                await self._human_like_behavior(page)
                
                # Esperar selector específico si se proporciona
                if config.wait_for_selector:
                    try:
                        await page.wait_for_selector(
                            config.wait_for_selector,
                            timeout=config.wait_for_timeout,
                            state="visible"
                        )
                    except PlaywrightTimeoutError:
                        logger.warning(f"Timeout esperando selector '{config.wait_for_selector}' en {url}")
                        # Continuar sin el selector si no aparece
                
                # Esperar más tiempo para asegurar que el contenido dinámico se cargue
                # Especialmente importante para sitios como TripAdvisor
                wait_time = 3 if "tripadvisor" in url.lower() else 2
                await asyncio.sleep(wait_time)
                
                # Obtener el HTML
                html = await page.content()
                
                # Validar contenido si está habilitado
                if config.validate_content and not await self._validate_content(html, url):
                    raise ValueError("Contenido inválido o bloqueado")
                
                # Retornar éxito
                return {
                    "success": True,
                    "url": url,
                    "status_code": status_code,
                    "html_length": len(html),
                    "attempt": attempt + 1
                }, html
                
            except PlaywrightTimeoutError as e:
                logger.warning(f"Timeout en intento {attempt + 1} para {url}: {e}")
                
                if attempt < config.max_retries - 1:
                    # Esperar antes de reintentar (exponential backoff)
                    await asyncio.sleep(config.retry_delay * (2 ** attempt))
                    continue
                
                return {
                    "error": "Timeout_Playwright",
                    "url": url,
                    "details": f"Timeout después de {config.max_retries} intentos",
                    "attempts": config.max_retries
                }, ""
                
            except Exception as e:
                logger.error(f"Error en intento {attempt + 1} para {url}: {e}")
                
                if attempt < config.max_retries - 1:
                    # Esperar antes de reintentar
                    await asyncio.sleep(config.retry_delay * (2 ** attempt))
                    continue
                
                error_type = type(e).__name__
                return {
                    "error": f"Excepcion_Playwright_{error_type}",
                    "url": url,
                    "details": str(e),
                    "attempts": config.max_retries
                }, ""
                
            finally:
                # Cerrar página
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                
                # Cerrar contexto
                if context:
                    try:
                        await context.close()
                    except Exception:
                        pass
    
    async def process_urls_batch(
        self,
        urls: List[str],
        process_func: Callable,
        config: Optional[PlaywrightConfig] = None,
        max_concurrent: int = 3,  # Reducido de 5 para mayor estabilidad
        progress_callback: Optional[Callable] = None
    ) -> List[Any]:
        """
        Procesa múltiples URLs en lote usando Playwright con optimizaciones.
        
        Args:
            urls: Lista de URLs a procesar
            process_func: Función para procesar cada resultado (url, html, browser) -> result
            config: Configuración opcional de Playwright
            max_concurrent: Número máximo de páginas concurrentes
            progress_callback: Callback para reportar progreso
            
        Returns:
            Lista de resultados procesados
        """
        config = config or self.config
        results = []
        
        async with async_playwright() as p:
            # Lanzar navegador con configuración optimizada
            browser = await p.chromium.launch(
                headless=config.headless,
                args=config.browser_args
            )
            
            try:
                # Semáforo para limitar concurrencia
                semaphore = asyncio.Semaphore(max_concurrent)
                
                # Tracking de URLs activas
                active_urls = set()
                completed_count = 0
                results_dict = {}  # Para mantener orden
                
                async def process_single_url(index: int, url: str):
                    nonlocal completed_count
                    
                    async with semaphore:
                        try:
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
                            
                            # Delay humano entre URLs del mismo dominio
                            if index > 0:
                                await asyncio.sleep(random.uniform(*config.human_delay_range))
                            
                            # Obtener HTML con reintentos
                            result_dict, html = await self.get_html(url, browser, config)
                            
                            # Procesar con la función proporcionada
                            if result_dict.get("success") and html:
                                processed_result = await process_func(url, html, browser)
                                results_dict[index] = processed_result
                            else:
                                results_dict[index] = result_dict
                                
                        except Exception as e:
                            logger.error(f"Error procesando {url}: {e}")
                            results_dict[index] = {
                                "error": "Error_Procesamiento",
                                "url": url,
                                "details": str(e)
                            }
                        finally:
                            # Remover de URLs activas y actualizar contador
                            active_urls.discard(url)
                            completed_count += 1
                            
                            if progress_callback:
                                progress_info = {
                                    "message": f"Completado {completed_count}/{len(urls)}",
                                    "current_url": url,
                                    "active_urls": list(active_urls),
                                    "completed": completed_count,
                                    "total": len(urls),
                                    "remaining": len(urls) - completed_count
                                }
                                progress_callback(progress_info)
                
                # Crear tareas para todas las URLs
                tasks = [
                    process_single_url(i, url)
                    for i, url in enumerate(urls)
                ]
                
                # Ejecutar todas las tareas
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Reconstruir lista en orden original
                final_results = []
                for i in range(len(urls)):
                    if i in results_dict:
                        final_results.append(results_dict[i])
                    else:
                        final_results.append({
                            "error": "Resultado_Faltante",
                            "url": urls[i],
                            "details": "No se pudo obtener el resultado"
                        })
                
                return final_results
                
            finally:
                await browser.close()
    
    async def get_html_simple(
        self,
        url: str,
        config: Optional[PlaywrightConfig] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Función simplificada para obtener HTML de una sola URL.
        
        Args:
            url: URL a scrapear
            config: Configuración opcional de Playwright
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
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

def create_booking_config() -> PlaywrightConfig:
    """Crea una configuración específica para Booking.com"""
    return PlaywrightConfig(
        wait_for_selector="#hp_hotel_name, h1",
        wait_for_timeout=10000,
        wait_until="domcontentloaded"
    )


def create_tripadvisor_config() -> PlaywrightConfig:
    """Crea una configuración específica para TripAdvisor"""
    return PlaywrightConfig(
        wait_until="networkidle",  # TripAdvisor carga mucho contenido dinámico
        wait_for_selector=None,  # No esperar selector específico
        timeout=45000,  # Más tiempo para TripAdvisor
        wait_for_timeout=15000,
        block_resources=False,  # No bloquear recursos para TripAdvisor
        max_retries=3,  # Más reintentos para TripAdvisor
        human_delay_range=(3.0, 7.0),  # Delays más largos y humanos
        validate_content=False,  # No validar contenido
        browser_args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-notifications",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding"
        ]
    )


def create_generic_config(
    wait_for_selector: Optional[str] = None,
    timeout: int = 30000
) -> PlaywrightConfig:
    """Crea una configuración genérica personalizable"""
    return PlaywrightConfig(
        wait_for_selector=wait_for_selector,
        timeout=timeout,
        wait_for_timeout=10000,
        wait_until="domcontentloaded"
    )


def create_fast_config() -> PlaywrightConfig:
    """Crea una configuración rápida sin esperar a que se cargue todo"""
    return PlaywrightConfig(
        wait_until="domcontentloaded",
        timeout=20000,
        wait_for_timeout=5000,
        block_resources=True,
        validate_content=False  # Skip validation for speed
    )


def create_stealth_config() -> PlaywrightConfig:
    """Crea una configuración con máximas medidas anti-detección"""
    return PlaywrightConfig(
        wait_until="networkidle",  # Más lento pero más realista
        timeout=45000,
        wait_for_timeout=15000,
        block_resources=False,  # No bloquear nada para parecer más real
        max_retries=3,
        human_delay_range=(3.0, 7.0),  # Delays más humanos
        viewport={"width": 1920, "height": 1080},
        browser_args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security"
        ]
    )


def create_docker_optimized_config() -> PlaywrightConfig:
    """Crea una configuración optimizada para entornos Docker sin GUI"""
    return PlaywrightConfig(
        headless=True,  # Siempre headless en Docker
        wait_until="networkidle",
        timeout=45000,
        wait_for_timeout=15000,
        block_resources=False,
        max_retries=3,
        human_delay_range=(3.0, 7.0),
        validate_content=False,
        viewport={"width": 1920, "height": 1080},
        browser_args=[
            # Argumentos esenciales para Docker
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-zygote",
            "--single-process",  # Importante para contenedores
            "--disable-web-security",
            
            # Anti-detección
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--enable-features=NetworkService,NetworkServiceInProcess",
            
            # Optimizaciones de rendimiento
            "--disable-accelerated-2d-canvas",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            
            # Simular navegador real
            "--window-size=1920,1080",
            "--start-maximized",
            "--disable-notifications",
            "--disable-infobars",
            "--disable-breakpad",
            
            # Memoria y recursos
            "--memory-pressure-off",
            "--max_old_space_size=4096"
        ]
    )
