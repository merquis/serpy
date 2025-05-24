"""
Servicio base de Playwright para scraping reutilizable
Proporciona funcionalidad común para todos los servicios de scraping
"""
import asyncio
from typing import List, Dict, Optional, Tuple, Any, Callable
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
import logging

logger = logging.getLogger(__name__)


class PlaywrightConfig:
    """Configuración para las solicitudes de Playwright"""
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 60000,
        wait_until: str = "networkidle",
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        accept_language: str = "es-ES,es;q=0.9,en;q=0.8",
        ignore_https_errors: bool = True,
        wait_for_selector: Optional[str] = None,
        wait_for_timeout: int = 15000,
        extra_headers: Optional[Dict[str, str]] = None,
        browser_args: Optional[List[str]] = None
    ):
        self.headless = headless
        self.timeout = timeout
        self.wait_until = wait_until
        self.user_agent = user_agent
        self.accept_language = accept_language
        self.ignore_https_errors = ignore_https_errors
        self.wait_for_selector = wait_for_selector
        self.wait_for_timeout = wait_for_timeout
        self.extra_headers = extra_headers or {}
        self.browser_args = browser_args or ["--no-sandbox", "--disable-setuid-sandbox"]


class PlaywrightService:
    """Servicio base para operaciones con Playwright"""
    
    def __init__(self, config: Optional[PlaywrightConfig] = None):
        self.config = config or PlaywrightConfig()
    
    async def get_html(
        self,
        url: str,
        browser_instance: Browser,
        config: Optional[PlaywrightConfig] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Obtiene el HTML de una URL usando Playwright.
        
        Args:
            url: URL a scrapear
            browser_instance: Instancia del navegador Playwright
            config: Configuración opcional de Playwright
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        html = ""
        context = None
        page = None
        
        try:
            # Crear contexto del navegador
            context = await browser_instance.new_context(
                ignore_https_errors=config.ignore_https_errors
            )
            
            # Crear nueva página
            page = await context.new_page()
            
            # Configurar headers
            headers = {
                "User-Agent": config.user_agent,
                "Accept-Language": config.accept_language,
                **config.extra_headers
            }
            await page.set_extra_http_headers(headers)
            
            # Navegar a la URL
            response = await page.goto(
                url,
                timeout=config.timeout,
                wait_until=config.wait_until
            )
            
            status_code = response.status if response else 0
            
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
                "error": "Timeout_Playwright",
                "url": url,
                "details": f"Timeout al cargar la página: {str(e)}"
            }, ""
            
        except Exception as e:
            logger.error(f"Error al obtener HTML de {url}: {e}")
            error_type = type(e).__name__
            return {
                "error": f"Excepcion_Playwright_{error_type}",
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
    
    async def process_urls_batch(
        self,
        urls: List[str],
        process_func: Callable,
        config: Optional[PlaywrightConfig] = None,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> List[Any]:
        """
        Procesa múltiples URLs en lote usando Playwright.
        
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
            # Lanzar navegador
            browser = await p.chromium.launch(
                headless=config.headless,
                args=config.browser_args
            )
            
            try:
                # Semáforo para limitar concurrencia
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def process_single_url(index: int, url: str):
                    async with semaphore:
                        try:
                            if progress_callback:
                                progress_callback(f"Procesando {index+1}/{len(urls)}: {url}")
                            
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
        wait_for_timeout=15000
    )


def create_generic_config(
    wait_for_selector: Optional[str] = None,
    timeout: int = 30000
) -> PlaywrightConfig:
    """Crea una configuración genérica personalizable"""
    return PlaywrightConfig(
        wait_for_selector=wait_for_selector,
        timeout=timeout,
        wait_for_timeout=10000
    )


def create_fast_config() -> PlaywrightConfig:
    """Crea una configuración rápida sin esperar a que se cargue todo"""
    return PlaywrightConfig(
        wait_until="domcontentloaded",
        timeout=20000,
        wait_for_timeout=5000
    )
