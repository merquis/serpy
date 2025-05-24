"""
Servicio de HTTPX para scraping rápido con fallback a Playwright
Intenta primero con httpx (más rápido) y usa Playwright solo cuando es necesario
Incluye medidas anti-bot para evitar detección
"""
import httpx
import asyncio
import random
from typing import List, Dict, Optional, Tuple, Any, Callable
from bs4 import BeautifulSoup
import logging
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


class HttpxConfig:
    """Configuración para las solicitudes HTTPX con medidas anti-bot"""
    def __init__(
        self,
        timeout: int = 30,
        follow_redirects: bool = True,
        max_redirects: int = 10,
        user_agent: Optional[str] = None,
        accept_language: str = "es-ES,es;q=0.9,en;q=0.8",
        extra_headers: Optional[Dict[str, str]] = None,
        min_delay: float = 0.5,  # Delay mínimo entre requests
        max_delay: float = 2.0,  # Delay máximo entre requests
        rotate_user_agents: bool = True,
        use_http2: bool = True  # HTTP/2 para parecer más real
    ):
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.user_agent = user_agent
        self.accept_language = accept_language
        self.extra_headers = extra_headers or {}
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.rotate_user_agents = rotate_user_agents
        self.use_http2 = use_http2
        
        # Inicializar generador de user agents si es necesario
        if self.rotate_user_agents:
            try:
                self.ua_generator = UserAgent()
            except:
                # Fallback si fake_useragent falla
                self.ua_generator = None
                self.user_agents_pool = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
                ]


class HttpxService:
    """Servicio para operaciones con HTTPX con medidas anti-bot"""
    
    def __init__(self, config: Optional[HttpxConfig] = None):
        self.config = config or HttpxConfig()
        self.last_request_time = {}  # Para controlar delays por dominio
    
    def _get_random_user_agent(self) -> str:
        """Obtiene un User-Agent aleatorio"""
        if self.config.rotate_user_agents:
            if self.config.ua_generator:
                try:
                    return self.config.ua_generator.random
                except:
                    pass
            # Fallback a pool local
            return random.choice(self.config.user_agents_pool)
        else:
            return self.config.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def _get_headers(self, url: str) -> Dict[str, str]:
        """Genera headers realistas para evitar detección"""
        # Headers base que imitan un navegador real
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": self.config.accept_language,
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        # Añadir referer aleatorio ocasionalmente
        if random.random() > 0.5:
            referers = [
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://duckduckgo.com/",
                f"https://{url.split('/')[2]}/"  # Same domain
            ]
            headers["Referer"] = random.choice(referers)
        
        # Añadir headers adicionales
        headers.update(self.config.extra_headers)
        
        return headers
    
    async def _apply_delay(self, domain: str):
        """Aplica un delay aleatorio entre requests al mismo dominio"""
        current_time = asyncio.get_event_loop().time()
        
        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            
            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)
        
        self.last_request_time[domain] = asyncio.get_event_loop().time()
    
    async def get_html(
        self,
        url: str,
        config: Optional[HttpxConfig] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Obtiene el HTML de una URL usando HTTPX con medidas anti-bot.
        
        Args:
            url: URL a scrapear
            config: Configuración opcional de HTTPX
            
        Returns:
            Tupla con (resultado_dict, html_content)
        """
        config = config or self.config
        
        # Extraer dominio para control de delays
        try:
            domain = url.split('/')[2]
        except:
            domain = url
        
        # Aplicar delay anti-bot
        await self._apply_delay(domain)
        
        # Configurar headers con rotación
        headers = self._get_headers(url)
        
        try:
            # Configurar cliente con opciones anti-bot
            async with httpx.AsyncClient(
                timeout=config.timeout,
                follow_redirects=config.follow_redirects,
                max_redirects=config.max_redirects,
                headers=headers,
                http2=config.use_http2,
                verify=True,  # Verificar SSL como un navegador real
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=30
                )
            ) as client:
                # Añadir cookies vacías para parecer más real
                client.cookies.set("test", "1", domain=domain)
                
                response = await client.get(url)
                
                # Si el status es 200, devolver el HTML
                if response.status_code == 200:
                    html = response.text
                    
                    # Verificar que tengamos contenido HTML válido
                    if html and len(html) > 100:  # Mínimo de contenido
                        # Verificar si parece ser una página de bloqueo
                        lower_html = html.lower()
                        if any(blocked in lower_html for blocked in [
                            'cloudflare', 'cf-ray', 'access denied', 'forbidden',
                            'bot detection', 'captcha', 'recaptcha', 'robot'
                        ]):
                            logger.warning(f"Posible bloqueo detectado en {url}")
                            return {
                                "error": "Posible_Bloqueo",
                                "url": url,
                                "status_code": response.status_code,
                                "details": "Detectado posible sistema anti-bot",
                                "method": "httpx",
                                "needs_playwright": True
                            }, ""
                        
                        return {
                            "success": True,
                            "url": url,
                            "status_code": response.status_code,
                            "html_length": len(html),
                            "method": "httpx"
                        }, html
                    else:
                        return {
                            "error": "HTML_Insuficiente",
                            "url": url,
                            "status_code": response.status_code,
                            "details": "El contenido HTML es muy corto o vacío",
                            "method": "httpx",
                            "needs_playwright": True
                        }, ""
                else:
                    # Status diferente a 200, necesitará Playwright
                    return {
                        "error": f"Status_{response.status_code}",
                        "url": url,
                        "status_code": response.status_code,
                        "details": f"Status code: {response.status_code}",
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
                    
                    # Intentar primero con HTTPX
                    result_dict, html = await self.get_html(url, config)
                    
                    if result_dict.get("success") and html:
                        # HTTPX exitoso, procesar el resultado
                        logger.info(f"✅ HTTPX exitoso para {url}")
                        processed_result = await process_func(url, html, "httpx")
                        results_dict[index] = processed_result
                    elif result_dict.get("needs_playwright"):
                        # Necesita Playwright, usar el servicio de fallback
                        logger.info(f"🎭 Usando Playwright para {url} debido a: {result_dict.get('error')}")
                        
                        # Obtener HTML con Playwright
                        from playwright.async_api import async_playwright
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
                                    processed_result = await process_func(url, pw_html, browser)
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


# Funciones helper para configuraciones comunes

def create_fast_httpx_config() -> HttpxConfig:
    """Crea una configuración rápida para HTTPX con anti-bot básico"""
    return HttpxConfig(
        timeout=15,
        follow_redirects=True,
        min_delay=0.3,
        max_delay=1.0
    )


def create_stealth_httpx_config() -> HttpxConfig:
    """Crea una configuración sigilosa con máximas medidas anti-bot"""
    return HttpxConfig(
        timeout=30,
        follow_redirects=True,
        min_delay=1.0,
        max_delay=3.0,
        rotate_user_agents=True,
        use_http2=True
    )


def create_aggressive_httpx_config() -> HttpxConfig:
    """Crea una configuración agresiva con delays mínimos (usar con cuidado)"""
    return HttpxConfig(
        timeout=10,
        follow_redirects=True,
        min_delay=0.1,
        max_delay=0.5,
        rotate_user_agents=True
    )
