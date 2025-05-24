"""
Servicio de HTTPX para scraping rápido con fallback a Playwright
Intenta primero con httpx (más rápido) y usa Playwright solo cuando es necesario
Incluye medidas anti-bot para evitar detección y manejo de cookies/captchas
"""
import httpx
import asyncio
import random
import time
from typing import List, Dict, Optional, Tuple, Any, Callable, Union
from bs4 import BeautifulSoup
import logging
from fake_useragent import UserAgent
import cloudscraper

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
        use_http2: bool = True,  # HTTP/2 para parecer más real
        handle_cookies: bool = True,  # Manejar cookies automáticamente
        use_cloudscraper: bool = False,  # Usar cloudscraper para bypass de Cloudflare
        accept_all_cookies: bool = True  # Aceptar todas las cookies automáticamente
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
        self.handle_cookies = handle_cookies
        self.use_cloudscraper = use_cloudscraper
        self.accept_all_cookies = accept_all_cookies
        
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
        self.cookie_jars = {}  # Almacenar cookies por dominio
        
        # Inicializar cloudscraper si está habilitado
        if self.config.use_cloudscraper:
            self.scraper = cloudscraper.create_scraper()
    
    def _get_random_user_agent(self) -> str:
        """Obtiene un User-Agent aleatorio"""
        if self.config.rotate_user_agents:
            if self.config.ua_generator:
                try:
                    return self.config.ua_generator.random
                except:
                    pass
            # Fallback a pool local
            if hasattr(self.config, 'user_agents_pool'):
                return random.choice(self.config.user_agents_pool)
        
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
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
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
        
        # Headers específicos para ciertos dominios
        domain = url.split('/')[2].lower()
        if 'tripadvisor' in domain:
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            headers["Sec-Fetch-Site"] = "same-origin"
            headers["Sec-Fetch-Mode"] = "navigate"
        elif 'destinia' in domain:
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            headers["Sec-Fetch-Site"] = "cross-site"
        
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
    
    def _apply_delay_sync(self, domain: str):
        """Aplica un delay aleatorio entre requests al mismo dominio (versión síncrona)"""
        current_time = time.time()
        
        if domain in self.last_request_time:
            elapsed = current_time - self.last_request_time[domain]
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            
            if elapsed < delay:
                time.sleep(delay - elapsed)
        
        self.last_request_time[domain] = time.time()
    
    def _check_if_blocked(self, html: str, status_code: int) -> Tuple[bool, str]:
        """
        Verifica si la respuesta indica un bloqueo o necesita Playwright
        
        Returns:
            Tuple[bool, str]: (necesita_playwright, razón)
        """
        # Primero verificar el código de estado
        if status_code != 200:
            # Códigos que definitivamente necesitan Playwright
            if status_code in [403, 429, 503]:
                return True, f"Status_{status_code}_Bloqueado"
            # Códigos 3xx (redirecciones) pueden funcionar con httpx
            elif 300 <= status_code < 400:
                return False, ""
            # Otros códigos 4xx/5xx probablemente necesiten Playwright
            elif status_code >= 400:
                return True, f"Status_{status_code}_Error"
        
        # Si el status es 200, verificar el contenido
        if html:
            lower_html = html.lower()
            
            # Detectar sistemas anti-bot conocidos
            blocking_indicators = [
                ('cloudflare', 'cf-ray', 'cf-browser-verification'),
                ('access denied', 'forbidden', 'blocked'),
                ('bot detection', 'robot detection'),
                ('captcha', 'recaptcha', 'hcaptcha'),
                ('please enable javascript', 'javascript is required'),
                ('checking your browser', 'verificando tu navegador'),
                ('ddos protection', 'under attack mode'),
                ('rate limit', 'too many requests'),
                ('enable cookies', 'accept cookies', 'cookie consent')
            ]
            
            for indicators in blocking_indicators:
                if any(indicator in lower_html for indicator in indicators):
                    return True, f"Bloqueado_por_{indicators[0].replace(' ', '_')}"
            
            # Verificar si la página parece cargar contenido con JavaScript
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Verificar si hay contenido útil (headers)
            has_h1 = bool(soup.find('h1'))
            has_h2 = bool(soup.find('h2'))
            has_h3 = bool(soup.find('h3'))
            has_headers = has_h1 or has_h2 or has_h3
            
            # 2. Verificar indicadores de carga con JavaScript
            js_indicators = [
                # Frameworks JavaScript comunes
                'react-root', '__next', 'vue-app', 'ng-app', 'angular',
                # Indicadores de carga dinámica
                'loading', 'spinner', 'skeleton',
                # Scripts de frameworks
                'webpack', 'bundle.js', 'app.js', 'main.js',
                # Contenedores vacíos típicos de SPAs
                '<div id="root"></div>', '<div id="app"></div>',
                # Meta tags de frameworks
                'data-react', 'data-vue', 'data-ng',
                # Indicadores de lazy loading
                'lazy-load', 'lazyload', 'data-src'
            ]
            
            has_js_indicators = any(indicator in lower_html for indicator in js_indicators)
            
            # 3. Verificar si el body está casi vacío (típico de SPAs)
            body = soup.find('body')
            if body:
                # Contar elementos significativos en el body
                significant_tags = body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article', 'section', 'main'])
                has_significant_content = len(significant_tags) > 2
            else:
                has_significant_content = False
            
            # 4. Verificar si hay muchos scripts (indicador de SPA)
            scripts = soup.find_all('script')
            has_many_scripts = len(scripts) > 10
            
            # 5. Verificar noscript tags (sitios que requieren JS)
            has_noscript = bool(soup.find('noscript'))
            
            # Decisión: necesita Playwright si:
            # - No hay headers Y hay indicadores de JS
            # - No hay contenido significativo Y hay muchos scripts
            # - Hay tags noscript (indica que el sitio requiere JS)
            if status_code == 200:
                if not has_headers and (has_js_indicators or has_many_scripts):
                    return True, "Sin_headers_posible_JavaScript"
                elif not has_significant_content and has_many_scripts:
                    return True, "Contenido_mínimo_muchos_scripts"
                elif has_noscript and not has_headers:
                    return True, "Requiere_JavaScript"
        
        # Si llegamos aquí, el contenido parece válido
        return False, ""
    
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
        
        # Si está habilitado cloudscraper, intentar primero con él
        if config.use_cloudscraper:
            try:
                response = self.scraper.get(url, headers=self._get_headers(url))
                if response.status_code == 200:
                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.status_code,
                        "html_length": len(response.text),
                        "method": "cloudscraper"
                    }, response.text
            except Exception as e:
                logger.warning(f"Cloudscraper falló para {url}: {e}")
        
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
                # Manejar cookies si está habilitado
                if config.handle_cookies and domain in self.cookie_jars:
                    for cookie in self.cookie_jars[domain]:
                        client.cookies.set(cookie['name'], cookie['value'], domain=domain)
                
                # Añadir cookies de aceptación si está habilitado
                if config.accept_all_cookies:
                    client.cookies.set("cookieconsent_status", "allow", domain=domain)
                    client.cookies.set("cookie_consent", "accepted", domain=domain)
                    client.cookies.set("gdpr_consent", "1", domain=domain)
                
                response = await client.get(url)
                
                # Guardar cookies para futuras peticiones
                if config.handle_cookies:
                    self.cookie_jars[domain] = [
                        {"name": k, "value": v} for k, v in client.cookies.items()
                    ]
                
                html = response.text
                
                # Verificar si está bloqueado o necesita Playwright
                needs_playwright, reason = self._check_if_blocked(html, response.status_code)
                
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
        
        # Extraer dominio para control de delays
        try:
            domain = url.split('/')[2]
        except:
            domain = url
        
        # Aplicar delay anti-bot
        self._apply_delay_sync(domain)
        
        # Si está habilitado cloudscraper, intentar primero con él
        if config.use_cloudscraper:
            try:
                response = self.scraper.get(url, headers=self._get_headers(url), timeout=config.timeout)
                if response.status_code == 200:
                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.status_code,
                        "html_length": len(response.text),
                        "method": "cloudscraper"
                    }, response.text
            except Exception as e:
                logger.warning(f"Cloudscraper falló para {url}: {e}")
        
        # Configurar headers con rotación
        headers = self._get_headers(url)
        
        try:
            # Configurar cliente síncrono
            with httpx.Client(
                timeout=config.timeout,
                follow_redirects=config.follow_redirects,
                max_redirects=config.max_redirects,
                headers=headers,
                http2=config.use_http2,
                verify=True
            ) as client:
                # Manejar cookies
                if config.handle_cookies and domain in self.cookie_jars:
                    for cookie in self.cookie_jars[domain]:
                        client.cookies.set(cookie['name'], cookie['value'], domain=domain)
                
                # Añadir cookies de aceptación
                if config.accept_all_cookies:
                    client.cookies.set("cookieconsent_status", "allow", domain=domain)
                    client.cookies.set("cookie_consent", "accepted", domain=domain)
                    client.cookies.set("gdpr_consent", "1", domain=domain)
                
                response = client.get(url)
                
                # Guardar cookies
                if config.handle_cookies:
                    self.cookie_jars[domain] = [
                        {"name": k, "value": v} for k, v in client.cookies.items()
                    ]
                
                html = response.text
                
                # Verificar si está bloqueado
                needs_playwright, reason = self._check_if_blocked(html, response.status_code)
                
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
        request_headers = self._get_headers(url)
        if headers:
            request_headers.update(headers)
        
        try:
            with httpx.Client(
                timeout=config.timeout,
                follow_redirects=config.follow_redirects,
                headers=request_headers,
                http2=config.use_http2,
                verify=True
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
    """Crea una configuración rápida para HTTPX con anti-bot básico"""
    return HttpxConfig(
        timeout=15,
        follow_redirects=True,
        min_delay=0.3,
        max_delay=1.0,
        use_cloudscraper=False
    )


def create_stealth_httpx_config() -> HttpxConfig:
    """Crea una configuración sigilosa con máximas medidas anti-bot"""
    return HttpxConfig(
        timeout=30,
        follow_redirects=True,
        min_delay=1.0,
        max_delay=3.0,
        rotate_user_agents=True,
        use_http2=True,
        use_cloudscraper=True,
        accept_all_cookies=True
    )


def create_aggressive_httpx_config() -> HttpxConfig:
    """Crea una configuración agresiva con delays mínimos (usar con cuidado)"""
    return HttpxConfig(
        timeout=10,
        follow_redirects=True,
        min_delay=0.1,
        max_delay=0.5,
        rotate_user_agents=True,
        use_cloudscraper=False
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
