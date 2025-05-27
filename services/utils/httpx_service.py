"""
Servicio de HTTPX para scraping rápido con fallback a Playwright
Intenta primero con httpx (más rápido) y usa Playwright solo cuando es necesario
rebrowser-playwright maneja automáticamente todas las medidas anti-bot
"""
import httpx
import asyncio
from typing import List, Dict, Optional, Tuple, Any, Callable
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class HttpxConfig:
    """Configuración básica para las solicitudes HTTPX"""
    def __init__(
        self,
        timeout: int = 30,
        follow_redirects: bool = True,
        max_redirects: int = 10,
        extra_headers: Optional[Dict[str, str]] = None
    ):
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.extra_headers = extra_headers or {}


class HttpxService:
    """Servicio básico para operaciones con HTTPX"""
    
    def __init__(self, config: Optional[HttpxConfig] = None):
        self.config = config or HttpxConfig()
    
    def _check_if_blocked(self, html: str, status_code: int, url: str) -> Tuple[bool, str]:
        """
        Verifica si la respuesta necesita Playwright
        
        Returns:
            Tuple[bool, str]: (necesita_playwright, razón)
        """
        if status_code != 200:
            # Códigos de error que necesitan Playwright
            if status_code in [403, 429, 503]:
                return True, f"Status_{status_code}_Bloqueado"
            elif status_code >= 400:
                return True, f"Status_{status_code}_Error"
        
        # Si el status es 200, verificar el contenido
        if html and status_code == 200:
            soup = BeautifulSoup(html, 'html.parser')
            
            # NUEVA LÓGICA: Verificar que haya al menos un H2 con letras de la a-z
            h2_tags = soup.find_all('h2')
            has_valid_h2 = False
            
            import re
            for h2 in h2_tags:
                text = h2.get_text(strip=True)
                # Verificar si contiene al menos una letra (a-z o A-Z)
                if text and re.search(r'[a-zA-Z]', text):
                    has_valid_h2 = True
                    break
            
            # Si no hay H2 válido, necesita Playwright
            if not has_valid_h2:
                return True, "Sin_H2_valido_usar_Playwright"
            
            # Verificar indicadores de bloqueo
            lower_html = html.lower()
            blocking_indicators = [
                'cloudflare', 'cf-ray',
                'access denied', 'forbidden', 'blocked',
                'bot detection', 'robot detection',
                'captcha', 'recaptcha', 'hcaptcha',
                'please enable javascript', 'javascript is required',
                'checking your browser'
            ]
            
            for indicator in blocking_indicators:
                if indicator in lower_html:
                    return True, f"Bloqueado_por_{indicator.replace(' ', '_')}"
        
        # Si llegamos aquí, el contenido parece válido
        return False, ""
    
    async def get_html(
        self,
        url: str,
        config: Optional[HttpxConfig] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Obtiene el HTML de una URL usando HTTPX básico.
        
        Args:
            url: URL a scrapear
            config: Configuración opcional de HTTPX
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        
        try:
            # Cliente HTTPX básico sin medidas anti-bot
            async with httpx.AsyncClient(
                timeout=config.timeout,
                follow_redirects=config.follow_redirects,
                max_redirects=config.max_redirects,
                headers=config.extra_headers
            ) as client:
                response = await client.get(url)
                html = response.text
                
                # Verificar si necesita Playwright
                needs_playwright, reason = self._check_if_blocked(html, response.status_code, url)
                
                if not needs_playwright and response.status_code == 200:
                    # Éxito con httpx
                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.status_code,
                        "html_length": len(html),
                        "method": "httpx"
                    }, html
                else:
                    # Necesita Playwright
                    return {
                        "error": reason or f"Status_{response.status_code}",
                        "url": url,
                        "status_code": response.status_code,
                        "details": f"Necesita Playwright: {reason}",
                        "method": "httpx",
                        "needs_playwright": True
                    }, ""
                    
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout con httpx para {url}: {e}")
            return {
                "error": "Timeout_Httpx",
                "url": url,
                "details": str(e),
                "method": "httpx",
                "needs_playwright": True
            }, ""
            
        except Exception as e:
            logger.warning(f"Error con httpx para {url}: {e}")
            return {
                "error": f"Error_Httpx_{type(e).__name__}",
                "url": url,
                "details": str(e),
                "method": "httpx",
                "needs_playwright": True
            }, ""
    
    def get_html_sync(
        self,
        url: str,
        config: Optional[HttpxConfig] = None,
        timeout: Optional[int] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Versión síncrona de get_html para reemplazar requests.get()
        
        Args:
            url: URL a scrapear
            config: Configuración opcional de HTTPX
            timeout: Timeout opcional (sobrescribe el de config)
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        if timeout:
            config.timeout = timeout
        
        try:
            # Cliente HTTPX básico sin medidas anti-bot
            with httpx.Client(
                timeout=config.timeout,
                follow_redirects=config.follow_redirects,
                max_redirects=config.max_redirects,
                headers=config.extra_headers
            ) as client:
                response = client.get(url)
                html = response.text
                
                # Verificar si necesita Playwright
                needs_playwright, reason = self._check_if_blocked(html, response.status_code, url)
                
                if not needs_playwright and response.status_code == 200:
                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.status_code,
                        "html_length": len(html),
                        "method": "httpx_sync"
                    }, html
                else:
                    return {
                        "error": reason or f"Status_{response.status_code}",
                        "url": url,
                        "status_code": response.status_code,
                        "details": f"Necesita Playwright: {reason}",
                        "method": "httpx_sync",
                        "needs_playwright": True
                    }, ""
                    
        except httpx.TimeoutException as e:
            logger.warning(f"Timeout con httpx para {url}: {e}")
            return {
                "error": "Timeout_Httpx",
                "url": url,
                "details": str(e),
                "method": "httpx_sync",
                "needs_playwright": True
            }, ""
            
        except Exception as e:
            logger.warning(f"Error con httpx para {url}: {e}")
            return {
                "error": f"Error_Httpx_{type(e).__name__}",
                "url": url,
                "details": str(e),
                "method": "httpx_sync",
                "needs_playwright": True
            }, ""
    
    def post_sync(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> httpx.Response:
        """
        Versión síncrona de POST para reemplazar requests.post()
        
        Args:
            url: URL para hacer POST
            data: Datos del formulario
            json: Datos JSON
            headers: Headers adicionales
            timeout: Timeout opcional
            
        Returns:
            httpx.Response object
        """
        config = self.config
        if timeout:
            config.timeout = timeout
        
        # Combinar headers
        request_headers = config.extra_headers.copy()
        if headers:
            request_headers.update(headers)
        
        try:
            with httpx.Client(
                timeout=config.timeout,
                follow_redirects=config.follow_redirects,
                headers=request_headers
            ) as client:
                response = client.post(url, data=data, json=json)
                return response
        except Exception as e:
            logger.error(f"Error en POST a {url}: {e}")
            raise
    
    async def process_urls_batch_with_fallback(
        self,
        urls: List[str],
        process_func: Callable,
        playwright_service: Any,  # PlaywrightService instance
        config: Optional[HttpxConfig] = None,
        playwright_config: Optional[Any] = None,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> List[Any]:
        """
        Procesa múltiples URLs primero con HTTPX, con fallback a Playwright.
        Mantiene el orden original de las URLs.
        
        Args:
            urls: Lista de URLs a procesar
            process_func: Función para procesar cada resultado (url, html, method) -> result
            playwright_service: Instancia del servicio Playwright para fallback
            config: Configuración opcional de HTTPX
            playwright_config: Configuración opcional de Playwright
            max_concurrent: Número máximo de requests concurrentes
            progress_callback: Callback para reportar progreso
            
        Returns:
            Lista de resultados procesados en el mismo orden que las URLs de entrada
        """
        config = config or self.config
        
        # Tracking de progreso
        active_urls = set()
        completed_count = 0
        results_dict = {}  # Diccionario para mantener resultados por índice
        
        # Semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(max_concurrent)
        
        import random

        async def process_single_url(index: int, url: str):
            nonlocal completed_count
            
            async with semaphore:
                try:
                    # Agregar a URLs activas
                    active_urls.add(url)
                    
                    # Espera aleatoria para simular comportamiento humano
                    await asyncio.sleep(random.uniform(1, 3))
                    
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
                    
                    # Intentar primero con HTTPX
                    result_dict, html = await self.get_html(url, config)
                    
                    if result_dict.get("success") and html:
                        # HTTPX exitoso, procesar el resultado
                        logger.info(f"✅ HTTPX exitoso para {url}")
                        processed_result = await process_func(url, html, "httpx")
                        if processed_result.get("needs_playwright"):
                            logger.info(f"🔁 Reintentando con Playwright tras resultado sin headers: {url}")
                            from rebrowser_playwright.async_api import async_playwright
                            async with async_playwright() as p:
                                browser = await p.chromium.launch(
                                    headless=playwright_config.headless if playwright_config else True,
                                    args=playwright_config.browser_args if playwright_config else ["--no-sandbox"]
                                )
                                try:
                                    pw_result, pw_html = await playwright_service.get_html(
                                        url, browser, playwright_config
                                    )
                                    if pw_result.get("success") and pw_html:
                                        processed_result = await process_func(url, pw_html, "playwright")
                                        results_dict[index] = processed_result
                                    else:
                                        results_dict[index] = pw_result
                                finally:
                                    await browser.close()
                        else:
                            results_dict[index] = processed_result
                    elif result_dict.get("needs_playwright"):
                        # Necesita Playwright, usar el servicio de fallback
                        logger.info(f"🎭 Usando Playwright para {url} debido a: {result_dict.get('error')}")
                        
                        # Obtener HTML con Playwright
                        from rebrowser_playwright.async_api import async_playwright
                        async with async_playwright() as p:
                            browser = await p.chromium.launch(
                                headless=playwright_config.headless if playwright_config else True,
                                args=playwright_config.browser_args if playwright_config else ["--no-sandbox"]
                            )
                            try:
                                pw_result, pw_html = await playwright_service.get_html(
                                    url, browser, playwright_config
                                )
                                
                                if pw_result.get("success") and pw_html:
                                    processed_result = await process_func(url, pw_html, "playwright")
                                    results_dict[index] = processed_result
                                else:
                                    results_dict[index] = pw_result
                            finally:
                                await browser.close()
                    else:
                        # Error sin necesidad de Playwright
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
        
        # Reconstruir la lista en el orden original
        ordered_results = []
        for i in range(len(urls)):
            if i in results_dict:
                ordered_results.append(results_dict[i])
            else:
                # Si por alguna razón no tenemos el resultado, agregar error
                ordered_results.append({
                    "error": "Resultado_Faltante",
                    "url": urls[i],
                    "details": "No se pudo obtener el resultado"
                })
        
        return ordered_results
    
    def extract_headers(self, html: str, levels: List[str] = None) -> Dict[str, List[str]]:
        """
        Extrae headers (h1, h2, h3, etc.) del HTML
        
        Args:
            html: Contenido HTML
            levels: Lista de niveles de headers a extraer (por defecto ['h1', 'h2', 'h3'])
            
        Returns:
            Diccionario con listas de headers por nivel
        """
        if levels is None:
            levels = ['h1', 'h2', 'h3']
        
        soup = BeautifulSoup(html, 'html.parser')
        headers = {}
        
        for level in levels:
            headers[level] = [tag.get_text(strip=True) for tag in soup.find_all(level)]
        
        return headers


# Funciones helper para configuraciones comunes

def create_fast_httpx_config() -> HttpxConfig:
    """Crea una configuración rápida para HTTPX"""
    return HttpxConfig(
        timeout=15,
        follow_redirects=True
    )


from services.utils.anti_bot_utils import get_realistic_headers

def create_stealth_httpx_config() -> HttpxConfig:
    """Crea una configuración anti-bot para HTTPX con cabeceras realistas y rotación de User-Agent"""
    return HttpxConfig(
        timeout=30,
        follow_redirects=True,
        extra_headers=get_realistic_headers()
    )


def create_aggressive_httpx_config() -> HttpxConfig:
    """Crea una configuración con timeout corto"""
    return HttpxConfig(
        timeout=10,
        follow_redirects=True
    )


# Clase de compatibilidad para reemplazar requests fácilmente
class HttpxRequests:
    """Clase de compatibilidad para reemplazar requests con httpx"""
    
    def __init__(self, config: Optional[HttpxConfig] = None):
        self.service = HttpxService(config)
    
    def get(self, url: str, timeout: int = 30, **kwargs) -> 'HttpxResponse':
        """Reemplazo directo para requests.get()"""
        result, html = self.service.get_html_sync(url, timeout=timeout)
        
        # Crear objeto de respuesta compatible
        response = HttpxResponse()
        response.url = url
        response.text = html
        response.status_code = result.get('status_code', 0)
        response.ok = result.get('success', False)
        response._result = result
        
        return response
    
    def post(self, url: str, data=None, json=None, headers=None, timeout=30) -> httpx.Response:
        """Reemplazo directo para requests.post()"""
        return self.service.post_sync(url, data=data, json=json, headers=headers, timeout=timeout)


class HttpxResponse:
    """Clase de respuesta compatible con requests.Response"""
    
    def __init__(self):
        self.url = ""
        self.text = ""
        self.status_code = 0
        self.ok = False
        self._result = {}
    
    def raise_for_status(self):
        """Lanza excepción si el status no es OK"""
        if not self.ok:
            raise httpx.HTTPStatusError(
                f"Error {self.status_code} para URL: {self.url}",
                request=None,
                response=None
            )


# Instancia global para reemplazo fácil de requests
httpx_requests = HttpxRequests()
