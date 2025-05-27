"""
Servicio mejorado de Tag Scraping con estrategia adaptativa de dos niveles
Implementa extracción exhaustiva de encabezados con técnicas anti-detección avanzadas
"""
import logging
import asyncio
import random
import time
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from bs4 import BeautifulSoup, Tag
import re
from urllib.parse import urlparse

from services.utils.httpx_service import HttpxService, HttpxConfig
from services.utils.playwright_service import PlaywrightService, PlaywrightConfig
from playwright.async_api import Browser, Page

logger = logging.getLogger(__name__)


@dataclass
class HeaderNode:
    """Nodo para representar un encabezado en la estructura jerárquica"""
    level: str  # h1, h2, h3
    text: str
    full_text: str = ""
    children: List['HeaderNode'] = field(default_factory=list)
    parent: Optional['HeaderNode'] = None
    element_index: int = 0  # Índice del elemento en el DOM
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el nodo a diccionario"""
        result = {
            "titulo": self.text,
            "texto": self.full_text
        }
        
        if self.level == "h1" and self.children:
            result["h2"] = []
            for child in self.children:
                if child.level == "h2":
                    h2_dict = {
                        "titulo": child.text,
                        "texto": child.full_text,
                        "h3": []
                    }
                    for h3_child in child.children:
                        if h3_child.level == "h3":
                            h3_dict = {
                                "titulo": h3_child.text,
                                "texto": h3_child.full_text
                            }
                            h2_dict["h3"].append(h3_dict)
                    result["h2"].append(h2_dict)
        
        return result


@dataclass
class ScrapingResult:
    """Resultado del scraping con información detallada"""
    url: str
    success: bool
    method: str  # httpx o playwright
    headers_found: Dict[str, int]  # Conteo de headers por nivel
    structure: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    details: Optional[str] = None
    status_code: int = 0
    title: str = ""
    description: str = ""
    extraction_time: float = 0.0
    retry_count: int = 0


class EnhancedTagScrapingService:
    """Servicio mejorado para extraer estructura jerárquica de etiquetas HTML"""

    def __init__(self):
        # Configuraciones anti-detección para HTTPX
        self.httpx_config = self._create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
        
        # Configuraciones anti-detección para Playwright
        self.playwright_config = self._create_stealth_playwright_config()
        self.playwright_service = PlaywrightService(self.playwright_config)
        
        # Cache de resultados para evitar re-scraping
        self._cache = {}
        self._cache_ttl = 3600  # 1 hora
        
        # Estadísticas de rendimiento
        self.stats = {
            "httpx_success": 0,
            "httpx_fail": 0,
            "playwright_success": 0,
            "playwright_fail": 0,
            "total_headers_found": defaultdict(int)
        }

    def _create_stealth_httpx_config(self) -> HttpxConfig:
        """Crea configuración HTTPX con máximas medidas anti-detección"""
        return HttpxConfig(
            timeout=30,
            follow_redirects=True,
            max_redirects=10,
            min_delay=1.0,
            max_delay=3.0,
            rotate_user_agents=True,
            use_http2=True,
            handle_cookies=True,
            use_cloudscraper=True,
            accept_all_cookies=True,
            extra_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )

    def _create_stealth_playwright_config(self) -> PlaywrightConfig:
        """Crea configuración Playwright con técnicas anti-detección avanzadas"""
        return PlaywrightConfig(
            headless=False,  # Navegador no headless es menos detectable
            timeout=60000,
            wait_until="networkidle",
            user_agent=None,  # Se establecerá dinámicamente
            accept_language="es-ES,es;q=0.9,en;q=0.8",
            ignore_https_errors=True,
            wait_for_selector=None,  # Dinámico según el sitio
            wait_for_timeout=20000,
            browser_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-infobars",
                "--disable-extensions",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection"
            ]
        )

    async def _apply_stealth_techniques(self, page: Page) -> None:
        """Aplica técnicas avanzadas anti-detección a la página de Playwright"""
        # Ocultar indicadores de automatización
        await page.add_init_script("""
            // Ocultar webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Modificar navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });
            
            // Modificar navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-ES', 'es', 'en-US', 'en']
            });
            
            // Ocultar automation
            Object.defineProperty(navigator, 'automation', {
                get: () => undefined
            });
            
            // Modificar permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Chrome específico
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Modificar toString de funciones
            const originalToString = Function.prototype.toString;
            Function.prototype.toString = function() {
                if (this === window.navigator.permissions.query) {
                    return 'function query() { [native code] }';
                }
                return originalToString.call(this);
            };
        """)
        
        # Configurar viewport aleatorio
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720}
        ]
        viewport = random.choice(viewports)
        await page.set_viewport_size(**viewport)
        
        # User agent aleatorio
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]
        await page.set_extra_http_headers({
            "User-Agent": random.choice(user_agents)
        })

    async def _simulate_human_behavior(self, page: Page) -> None:
        """Simula comportamiento humano en la página"""
        try:
            # Movimiento aleatorio del mouse
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Scroll aleatorio
            scroll_amount = random.randint(100, 300)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Pequeño scroll hacia arriba
            await page.evaluate(f"window.scrollBy(0, -{scroll_amount // 2})")
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
        except Exception as e:
            logger.debug(f"Error simulando comportamiento humano: {e}")

    def _extract_all_headers_from_soup(self, soup: BeautifulSoup) -> Dict[str, List[Tag]]:
        """Extrae TODOS los encabezados del DOM, incluyendo elementos ocultos y dinámicos"""
        headers = {
            "h1": [],
            "h2": [],
            "h3": []
        }
        
        # Buscar en TODO el DOM, sin restricciones
        for level in ["h1", "h2", "h3"]:
            # Buscar con múltiples estrategias
            
            # 1. Búsqueda estándar
            found_tags = soup.find_all(level)
            headers[level].extend(found_tags)
            
            # 2. Búsqueda case-insensitive
            found_tags_ci = soup.find_all(re.compile(f"^{level}$", re.I))
            for tag in found_tags_ci:
                if tag not in headers[level]:
                    headers[level].append(tag)
            
            # 3. Buscar en elementos con role="heading" y aria-level
            aria_level = level[1]  # "1", "2", o "3"
            role_headings = soup.find_all(attrs={"role": "heading", "aria-level": aria_level})
            for tag in role_headings:
                if tag not in headers[level]:
                    headers[level].append(tag)
            
            # 4. Buscar clases comunes que indican encabezados
            heading_classes = [
                f"{level}-title", f"{level}-heading", f"title-{level}",
                f"heading-{level}", f"{level}title", f"{level}heading"
            ]
            for class_name in heading_classes:
                class_tags = soup.find_all(class_=re.compile(class_name, re.I))
                for tag in class_tags:
                    if tag not in headers[level] and tag.get_text(strip=True):
                        headers[level].append(tag)
        
        # Eliminar duplicados manteniendo el orden
        for level in headers:
            seen = set()
            unique_headers = []
            for tag in headers[level]:
                tag_id = id(tag)
                if tag_id not in seen:
                    seen.add(tag_id)
                    unique_headers.append(tag)
            headers[level] = unique_headers
        
        return headers

    def _extract_text_content(self, element: Tag, soup: BeautifulSoup, max_length: int = 3000) -> str:
        """Extrae el texto asociado a un elemento de forma más exhaustiva"""
        text_parts = []
        seen_texts = set()
        
        # Obtener todos los elementos siguientes hasta el próximo encabezado
        current = element
        elements_to_check = []
        
        # 1. Buscar en siblings siguientes
        for sibling in element.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            elements_to_check.append(sibling)
        
        # 2. Buscar en elementos siguientes en el DOM
        for next_elem in element.find_all_next(limit=50):  # Limitar para evitar procesar todo el documento
            if next_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            if next_elem not in elements_to_check:
                elements_to_check.append(next_elem)
        
        # 3. Si el elemento está dentro de un contenedor, buscar en sus siblings
        parent = element.parent
        if parent and parent.name in ['div', 'section', 'article', 'main']:
            for child in parent.children:
                if child == element:
                    continue
                if hasattr(child, 'name') and child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    break
                if hasattr(child, 'name') and child not in elements_to_check:
                    elements_to_check.append(child)
        
        # Procesar elementos encontrados
        for elem in elements_to_check:
            if not hasattr(elem, 'name'):
                continue
                
            # Extraer texto de elementos relevantes
            if elem.name in ['p', 'div', 'span', 'li', 'td', 'th', 'blockquote', 'pre', 'code']:
                # Evitar elementos que son contenedores de otros ya procesados
                if any(parent in elements_to_check for parent in elem.parents):
                    continue
                
                text = elem.get_text(strip=True)
                
                # Filtros mejorados
                if self._is_valid_text(text) and text not in seen_texts:
                    text_parts.append(text)
                    seen_texts.add(text)
                    
                    # Verificar longitud acumulada
                    if len(' '.join(text_parts)) > max_length:
                        break
        
        # Unir y limpiar el texto
        full_text = ' '.join(text_parts)
        return self._clean_text(full_text)[:max_length]

    def _is_valid_text(self, text: str) -> bool:
        """Valida si el texto es contenido útil (no basura)"""
        if not text or len(text) < 10:
            return False
        
        # Patrones de texto no deseado
        junk_patterns = [
            r'^https?://',           # URLs
            r'^\w+\.\w+$',          # Dominios simples
            r'^[{}\[\]<>]+$',       # Solo símbolos de código
            r'^\d+$',               # Solo números
            r'^[A-Z_]+$',           # Solo mayúsculas (constantes)
            r'^(var|let|const|function|class|import|export)\s',  # JavaScript
            r'^(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)\s',      # SQL
            r'^\s*[{}]\s*$',        # Llaves vacías
            r'^(true|false|null|undefined)$',  # Valores JS
            r'^\w+:\s*\w+;?$',      # CSS properties
        ]
        
        for pattern in junk_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return False
        
        # Verificar proporción de caracteres especiales
        special_chars = sum(1 for c in text if c in '{}[]<>()=;:@#$%^&*')
        if special_chars > len(text) * 0.3:
            return False
        
        # Verificar que tenga al menos algunas palabras reales
        words = text.split()
        if len(words) < 3:
            return False
        
        # Verificar que no sea todo en mayúsculas (excepto títulos cortos)
        if text.isupper() and len(text) > 50:
            return False
        
        return True

    def _clean_text(self, text: str) -> str:
        """Limpia el texto eliminando espacios extras y formateando correctamente"""
        if not text:
            return ""
        
        # Normalizar espacios en blanco
        text = re.sub(r'\s+', ' ', text)
        
        # Eliminar espacios antes/después de puntuación
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([.,;:!?])\s*', r'\1 ', text)
        
        # Eliminar múltiples signos de puntuación
        text = re.sub(r'([.,;:!?]){2,}', r'\1', text)
        
        # Capitalizar después de puntos
        text = re.sub(r'(\. )([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
        
        return text.strip()

    def _build_header_tree(self, headers: Dict[str, List[Tag]], soup: BeautifulSoup) -> Optional[HeaderNode]:
        """Construye un árbol jerárquico de encabezados con su contenido asociado"""
        if not headers.get("h1"):
            return None
        
        # Tomar el primer H1
        h1_tag = headers["h1"][0]
        h1_node = HeaderNode(
            level="h1",
            text=h1_tag.get_text(strip=True),
            full_text=self._extract_text_content(h1_tag, soup),
            element_index=self._get_element_index(h1_tag, soup)
        )
        
        # Obtener todos los elementos y sus índices
        all_headers = []
        for level in ["h1", "h2", "h3"]:
            for tag in headers.get(level, []):
                all_headers.append({
                    "tag": tag,
                    "level": level,
                    "index": self._get_element_index(tag, soup),
                    "text": tag.get_text(strip=True)
                })
        
        # Ordenar por posición en el documento
        all_headers.sort(key=lambda x: x["index"])
        
        # Construir el árbol
        current_h2 = None
        h1_index = h1_node.element_index
        
        for header in all_headers:
            if header["index"] <= h1_index:
                continue
                
            # Si encontramos otro H1, detenemos
            if header["level"] == "h1":
                break
            
            # Procesar H2
            elif header["level"] == "h2":
                h2_node = HeaderNode(
                    level="h2",
                    text=header["text"],
                    full_text=self._extract_text_content(header["tag"], soup),
                    parent=h1_node,
                    element_index=header["index"]
                )
                h1_node.children.append(h2_node)
                current_h2 = h2_node
            
            # Procesar H3
            elif header["level"] == "h3" and current_h2:
                h3_node = HeaderNode(
                    level="h3",
                    text=header["text"],
                    full_text=self._extract_text_content(header["tag"], soup),
                    parent=current_h2,
                    element_index=header["index"]
                )
                current_h2.children.append(h3_node)
        
        return h1_node

    def _get_element_index(self, element: Tag, soup: BeautifulSoup) -> int:
        """Obtiene el índice de un elemento en el documento"""
        all_elements = list(soup.descendants)
        try:
            return all_elements.index(element)
        except ValueError:
            return -1

    async def _validate_httpx_result(self, html: str, url: str) -> Tuple[bool, str]:
        """Valida si el resultado de HTTPX es suficiente o necesita Playwright"""
        if not html:
            return False, "HTML vacío"
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar H1 y H2
        h1_tags = soup.find_all('h1')
        h2_tags = soup.find_all('h2')
        
        # Validación principal: debe tener al menos un H1 y un H2
        if not h1_tags:
            return False, "Sin etiquetas H1"
        
        if not h2_tags:
            return False, "Sin etiquetas H2"
        
        # Validación adicional: el H1 debe tener contenido significativo
        h1_text = h1_tags[0].get_text(strip=True)
        if len(h1_text) < 3:
            return False, "H1 sin contenido significativo"
        
        return True, "Validación exitosa"

    async def scrape_single_url(self, url: str, force_playwright: bool = False) -> ScrapingResult:
        """Scraping de una sola URL con estrategia de dos niveles"""
        start_time = time.time()
        
        # Verificar cache
        cache_key = f"{url}:{force_playwright}"
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                logger.info(f"🎯 Usando resultado cacheado para {url}")
                return cached_result
        
        result = None
        
        # NIVEL 1: Intentar con HTTPX (si no se fuerza Playwright)
        if not force_playwright:
            logger.info(f"🚀 Intentando con HTTPX: {url}")
            
            try:
                httpx_result, html = await self.httpx_service.get_html(url, self.httpx_config)
                
                if httpx_result.get("success") and html:
                    # Validar el resultado
                    is_valid, validation_msg = await self._validate_httpx_result(html, url)
                    
                    if is_valid:
                        # Procesar con BeautifulSoup
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Extraer metadatos
                        title = soup.title.string.strip() if soup.title else ""
                        meta_desc = soup.find("meta", attrs={"name": "description"})
                        description = meta_desc.get("content", "").strip() if meta_desc else ""
                        
                        # Extraer TODOS los headers
                        headers = self._extract_all_headers_from_soup(soup)
                        
                        # Contar headers encontrados
                        headers_count = {
                            level: len(tags) for level, tags in headers.items()
                        }
                        
                        # Construir estructura jerárquica
                        header_tree = self._build_header_tree(headers, soup)
                        
                        if header_tree:
                            result = ScrapingResult(
                                url=url,
                                success=True,
                                method="httpx",
                                headers_found=headers_count,
                                structure=header_tree.to_dict(),
                                status_code=httpx_result.get("status_code", 200),
                                title=title,
                                description=description,
                                extraction_time=time.time() - start_time
                            )
                            
                            self.stats["httpx_success"] += 1
                            for level, count in headers_count.items():
                                self.stats["total_headers_found"][level] += count
                            
                            logger.info(f"✅ HTTPX exitoso para {url} - Headers: {headers_count}")
                        else:
                            logger.warning(f"⚠️ HTTPX sin estructura válida para {url}: {validation_msg}")
                            # Continuar a Playwright
                    else:
                        logger.warning(f"⚠️ Validación HTTPX falló para {url}: {validation_msg}")
                        # Continuar a Playwright
                else:
                    logger.warning(f"⚠️ HTTPX falló para {url}: {httpx_result.get('error', 'Unknown')}")
                    
            except Exception as e:
                logger.error(f"❌ Error con HTTPX para {url}: {e}")
                self.stats["httpx_fail"] += 1
        
        # NIVEL 2: Usar Playwright si HTTPX falló o fue insuficiente
        if not result:
            logger.info(f"🎭 Usando Playwright para {url}")
            
            try:
                from playwright.async_api import async_playwright
                
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=self.playwright_config.headless,
                        args=self.playwright_config.browser_args
                    )
                    
                    try:
                        context = await browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent=random.choice([
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            ])
                        )
                        
                        page = await context.new_page()
                        
                        # Aplicar técnicas anti-detección
                        await self._apply_stealth_techniques(page)
                        
                        # Navegar a la URL
                        response = await page.goto(
                            url,
                            timeout=self.playwright_config.timeout,
                            wait_until=self.playwright_config.wait_until
                        )
                        
                        status_code = response.status if response else 0
                        
                        # Simular comportamiento humano
                        await self._simulate_human_behavior(page)
                        
                        # Esperar un poco más para asegurar carga completa
                        await page.wait_for_timeout(3000)
                        
                        # Intentar hacer scroll para cargar contenido lazy
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1000)
                        await page.evaluate("window.scrollTo(0, 0)")
                        
                        # Obtener HTML renderizado
                        html = await page.content()
                        
                        if html:
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extraer metadatos
                            title = await page.title()
                            description = await page.evaluate("""
                                () => {
                                    const meta = document.querySelector('meta[name="description"]');
                                    return meta ? meta.content : '';
                                }
                            """)
                            
                            # Extraer headers con JavaScript para mayor precisión
                            js_headers = await page.evaluate("""
                                () => {
                                    const headers = {h1: [], h2: [], h3: []};
                                    
                                    // Buscar todos los H1, H2, H3
                                    ['h1', 'h2', 'h3'].forEach(tag => {
                                        const elements = document.querySelectorAll(tag);
                                        elements.forEach(el => {
                                            const text = el.textContent.trim();
                                            if (text) {
                                                headers[tag].push(text);
                                            }
                                        });
                                        
                                        // Buscar también por role y aria-level
                                        const ariaLevel = tag.substring(1);
                                        const roleElements = document.querySelectorAll(`[role="heading"][aria-level="${ariaLevel}"]`);
                                        roleElements.forEach(el => {
                                            const text = el.textContent.trim();
                                            if (text && !headers[tag].includes(text)) {
                                                headers[tag].push(text);
                                            }
                                        });
                                    });
                                    
                                    return headers;
                                }
                            """)
                            
                            # Combinar resultados de BeautifulSoup y JavaScript
                            headers = self._extract_all_headers_from_soup(soup)
                            
                            # Agregar headers encontrados por JavaScript que no estén en BeautifulSoup
                            for level in ["h1", "h2", "h3"]:
                                bs_texts = [tag.get_text(strip=True) for tag in headers[level]]
                                for js_text in js_headers.get(level, []):
                                    if js_text not in bs_texts:
                                        # Buscar el elemento en el soup para agregarlo
                                        matching_elements = soup.find_all(text=re.compile(re.escape(js_text)))
                                        for elem in matching_elements:
                                            if elem.parent and elem.parent not in headers[level]:
                                                headers[level].append(elem.parent)
                            
                            # Contar headers encontrados
                            headers_count = {
                                level: len(tags) for level, tags in headers.items()
                            }
                            
                            # Construir estructura jerárquica
                            header_tree = self._build_header_tree(headers, soup)
                            
                            if header_tree:
                                result = ScrapingResult(
                                    url=url,
                                    success=True,
                                    method="playwright",
                                    headers_found=headers_count,
                                    structure=header_tree.to_dict(),
                                    status_code=status_code,
                                    title=title,
                                    description=description,
                                    extraction_time=time.time() - start_time
                                )
                                
                                self.stats["playwright_success"] += 1
                                for level, count in headers_count.items():
                                    self.stats["total_headers_found"][level] += count
                                
                                logger.info(f"✅ Playwright exitoso para {url} - Headers: {headers_count}")
                            else:
                                result = ScrapingResult(
                                    url=url,
                                    success=False,
                                    method="playwright",
                                    headers_found={"h1": 0, "h2": 0, "h3": 0},
                                    error="Sin estructura válida",
                                    details="No se pudo construir estructura jerárquica",
                                    status_code=status_code,
                                    extraction_time=time.time() - start_time
                                )
                                self.stats["playwright_fail"] += 1
                        else:
                            result = ScrapingResult(
                                url=url,
                                success=False,
                                method="playwright",
                                headers_found={"h1": 0, "h2": 0, "h3": 0},
                                error="HTML vacío",
                                details="Playwright no pudo obtener contenido HTML",
                                status_code=status_code,
                                extraction_time=time.time() - start_time
                            )
                            self.stats["playwright_fail"] += 1
                            
                    finally:
                        await context.close()
                        await browser.close()
                        
            except Exception as e:
                logger.error(f"❌ Error con Playwright para {url}: {e}")
                result = ScrapingResult(
                    url=url,
                    success=False,
                    method="playwright",
                    headers_found={"h1": 0, "h2": 0, "h3": 0},
                    error=f"Error Playwright: {type(e).__name__}",
                    details=str(e),
                    extraction_time=time.time() - start_time
                )
                self.stats["playwright_fail"] += 1
        
        # Si no hay resultado, crear uno de error
        if not result:
            result = ScrapingResult(
                url=url,
                success=False,
                method="none",
                headers_found={"h1": 0, "h2": 0, "h3": 0},
                error="Sin resultado",
                details="No se pudo obtener resultado con ningún método",
                extraction_time=time.time() - start_time
            )
        
        # Guardar en cache
        self._cache[cache_key] = (time.time(), result)
        
        return result

    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Extrae estructura jerárquica de etiquetas HTML desde JSON"""
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []

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
            
            # Procesar URLs en lotes
            batch_results = await self._process_urls_batch(
                urls=urls,
                max_concurrent=max_concurrent,
                progress_callback=progress_callback
            )
            
            # Formatear resultados
            formatted_results = []
            for result in batch_results:
                if isinstance(result, ScrapingResult):
                    formatted_result = {
                        "url": result.url,
                        "status_code": result.status_code,
                        "method": result.method,
                        "headers_found": result.headers_found,
                        "extraction_time": result.extraction_time
                    }
                    
                    if result.success and result.structure:
                        formatted_result.update({
                            "title": result.title,
                            "description": result.description,
                            "h1": result.structure
                        })
                    else:
                        formatted_result.update({
                            "error": result.error,
                            "details": result.details
                        })
                    
                    formatted_results.append(formatted_result)
                else:
                    formatted_results.append(result)

            all_results.append({**context, "resultados": formatted_results})

        return all_results

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        """Extrae URLs de un item del JSON"""
        urls = []
        if "urls" in item:
            for u in item["urls"]:
                if isinstance(u, str):
                    urls.append(u)
                elif isinstance(u, dict) and "url" in u:
                    urls.append(u["url"])
        if "resultados" in item:
            for r in item["resultados"]:
                if isinstance(r, dict) and "url" in r:
                    urls.append(r["url"])
        return urls

    async def _process_urls_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> List[ScrapingResult]:
        """Procesa múltiples URLs en lote con concurrencia limitada"""
        semaphore = asyncio.Semaphore(max_concurrent)
        active_urls = set()
        completed_count = 0
        results = []
        
        async def process_single_url(index: int, url: str) -> ScrapingResult:
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
                    
                    # Procesar URL
                    result = await self.scrape_single_url(url)
                    
                    return result
                    
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
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Procesar excepciones
        final_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                final_results.append(ScrapingResult(
                    url=urls[i],
                    success=False,
                    method="error",
                    headers_found={"h1": 0, "h2": 0, "h3": 0},
                    error="Excepción durante procesamiento",
                    details=str(res),
                    extraction_time=0.0
                ))
            else:
                final_results.append(res)
        
        return final_results

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servicio"""
        total_success = self.stats["httpx_success"] + self.stats["playwright_success"]
        total_fail = self.stats["httpx_fail"] + self.stats["playwright_fail"]
        total_attempts = total_success + total_fail
        
        return {
            "total_attempts": total_attempts,
            "total_success": total_success,
            "total_fail": total_fail,
            "success_rate": (total_success / total_attempts * 100) if total_attempts > 0 else 0,
            "httpx": {
                "success": self.stats["httpx_success"],
                "fail": self.stats["httpx_fail"],
                "success_rate": (self.stats["httpx_success"] / (self.stats["httpx_success"] + self.stats["httpx_fail"]) * 100) 
                    if (self.stats["httpx_success"] + self.stats["httpx_fail"]) > 0 else 0
            },
            "playwright": {
                "success": self.stats["playwright_success"],
                "fail": self.stats["playwright_fail"],
                "success_rate": (self.stats["playwright_success"] / (self.stats["playwright_success"] + self.stats["playwright_fail"]) * 100)
                    if (self.stats["playwright_success"] + self.stats["playwright_fail"]) > 0 else 0
            },
            "headers_found": dict(self.stats["total_headers_found"])
        }

    def clear_cache(self) -> None:
        """Limpia la cache de resultados"""
        self._cache.clear()
        logger.info("Cache limpiada")

    def reset_stats(self) -> None:
        """Reinicia las estadísticas"""
        self.stats = {
            "httpx_success": 0,
            "httpx_fail": 0,
            "playwright_success": 0,
            "playwright_fail": 0,
            "total_headers_found": defaultdict(int)
        }
        logger.info("Estadísticas reiniciadas")


# Función helper para migración fácil desde el servicio anterior
def create_enhanced_tag_scraping_service() -> EnhancedTagScrapingService:
    """Crea una instancia del servicio mejorado de tag scraping"""
    return EnhancedTagScrapingService()
