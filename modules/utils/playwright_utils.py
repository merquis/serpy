"""
Utilidades de Playwright para scraping reutilizable
Este módulo proporciona funciones genéricas para capturar HTML usando Playwright
que pueden ser utilizadas por diferentes scrapers.
"""

import asyncio
from typing import List, Dict, Optional, Tuple, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError


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
        extra_headers: Optional[Dict[str, str]] = None
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


async def obtener_html_con_playwright(
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
        - resultado_dict: Diccionario con el resultado o error
        - html_content: Contenido HTML de la página
    """
    if config is None:
        config = PlaywrightConfig()
    
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
        await page.goto(
            url,
            timeout=config.timeout,
            wait_until=config.wait_until
        )
        
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
                "url_original": url,
                "details": "No se obtuvo contenido HTML."
            }, ""
        
        # Retornar éxito
        return {
            "success": True,
            "url_original": url,
            "html_length": len(html)
        }, html
        
    except PlaywrightTimeoutError as e:
        return {
            "error": "Timeout_Playwright",
            "url_original": url,
            "details": f"Timeout al cargar la página: {str(e)}"
        }, ""
        
    except Exception as e:
        error_type = type(e).__name__
        return {
            "error": f"Excepcion_Playwright_{error_type}",
            "url_original": url,
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


async def procesar_urls_en_lote(
    urls: List[str],
    config: Optional[PlaywrightConfig] = None,
    max_concurrent: int = 5
) -> List[Tuple[Dict[str, Any], str]]:
    """
    Procesa múltiples URLs en lote usando Playwright.
    
    Args:
        urls: Lista de URLs a procesar
        config: Configuración opcional de Playwright
        max_concurrent: Número máximo de páginas concurrentes
        
    Returns:
        Lista de tuplas (resultado_dict, html_content) para cada URL
    """
    results = []
    
    async with async_playwright() as p:
        # Lanzar navegador
        browser = await p.chromium.launch(headless=config.headless if config else True)
        
        # Procesar URLs en lotes para evitar sobrecarga
        for i in range(0, len(urls), max_concurrent):
            batch_urls = urls[i:i + max_concurrent]
            
            # Crear tareas para el lote actual
            tasks = [
                obtener_html_con_playwright(url, browser, config)
                for url in batch_urls
            ]
            
            # Ejecutar tareas del lote
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados del lote
            for j, res in enumerate(batch_results):
                url = batch_urls[j]
                if isinstance(res, Exception):
                    results.append(({
                        "error": "Excepcion_Gather",
                        "url_original": url,
                        "details": str(res)
                    }, ""))
                elif isinstance(res, tuple) and len(res) == 2:
                    results.append(res)
                else:
                    results.append(({
                        "error": "Resultado_Inesperado",
                        "url_original": url,
                        "details": str(res)
                    }, ""))
        
        # Cerrar navegador
        await browser.close()
    
    return results


async def obtener_html_simple(url: str, config: Optional[PlaywrightConfig] = None) -> Tuple[Dict[str, Any], str]:
    """
    Función simplificada para obtener HTML de una sola URL.
    
    Args:
        url: URL a scrapear
        config: Configuración opcional de Playwright
        
    Returns:
        Tupla con (resultado_dict, html_content)
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=config.headless if config else True)
        result = await obtener_html_con_playwright(url, browser, config)
        await browser.close()
        return result


# Funciones de utilidad adicionales

def crear_config_booking() -> PlaywrightConfig:
    """Crea una configuración específica para Booking.com"""
    return PlaywrightConfig(
        wait_for_selector="#hp_hotel_name, h1",
        wait_for_timeout=15000
    )


def crear_config_generica(
    wait_for_selector: Optional[str] = None,
    timeout: int = 30000
) -> PlaywrightConfig:
    """Crea una configuración genérica personalizable"""
    return PlaywrightConfig(
        wait_for_selector=wait_for_selector,
        timeout=timeout,
        wait_for_timeout=10000
    )
