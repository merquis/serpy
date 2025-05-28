import logging
from typing import List, Dict, Any, Optional, Callable
from services.utils.httpx_service import HttpxService, create_stealth_httpx_config
from rebrowser_playwright.async_api import async_playwright
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""

    def __init__(self):
        self.httpx_config = create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
        # Eliminado PlaywrightService, usaremos la versión minimalista directamente

    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """Extrae estructura jerárquica de etiquetas HTML desde JSON con fallback a Playwright"""
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

            async def process_func(url: str, html: str, method: str) -> Dict[str, Any]:
                import re
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    title = soup.title.string.strip() if soup.title else ""
                    meta = soup.find("meta", attrs={"name": "description"})
                    description = meta["content"].strip() if meta and meta.has_attr("content") else ""
                    h1_structure = self._extract_h1_structure(soup)

                    # Comprobación: ¿hay al menos un <h2> con una letra a-z?
                    h2s = []
                    if h1_structure and "h2" in h1_structure:
                        h2s = h1_structure["h2"]
                    has_valid_h2 = False
                    for h2 in h2s:
                        if "titulo" in h2 and re.search(r"[a-zA-Záéíóúüñ]", h2["titulo"], re.IGNORECASE):
                            has_valid_h2 = True
                            break

                    if not h1_structure or not h1_structure.get("titulo") or not has_valid_h2:
                        return {
                            "error": "Sin_headers_httpx" if not h1_structure or not h1_structure.get("titulo") else "Sin_h2_valido_httpx",
                            "url": url,
                            "status_code": 200,
                            "details": "No se detectaron encabezados válidos con httpx",
                            "method": method,
                            "needs_playwright": True
                        }

                    return {
                        "url": url,
                        "status_code": 200,
                        "title": title,
                        "description": description,
                        "h1": h1_structure,
                        "method": method
                    }
                except Exception as e:
                    logger.error(f"Error procesando {url}: {e}")
                    return {
                        "url": url,
                        "status_code": "error",
                        "error": str(e),
                        "method": method
                    }

            results = await self.httpx_service.process_urls_batch_with_fallback(
                urls=urls,
                process_func=process_func,
                playwright_service=None,  # No se usa
                config=self.httpx_config,
                playwright_config=None,  # No se usa
                max_concurrent=max_concurrent,
                progress_callback=progress_callback,
                # Fallback manual a Playwright minimalista
                fallback_func=self._minimalist_playwright_fallback
            )

            all_results.append({**context, "resultados": results})

        return all_results

    async def _minimalist_playwright_fallback(self, url: str) -> str:
        """
        Fallback minimalista: solo obtiene el HTML usando rebrowser-playwright sin lógica extra.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            html = await page.content()
            await browser.close()
            return html

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
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

    def _extract_h1_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae la estructura jerárquica de encabezados H1, H2 y H3 con su texto asociado"""
        # Encontrar el primer H1
        h1_element = soup.find('h1')
        if not h1_element:
            return {}
        
        # Crear estructura del H1
        h1_data = {
            "titulo": h1_element.get_text(strip=True),
            "texto": self._extract_text_after_element(h1_element, soup),
            "h2": []
        }
        
        # Obtener todos los elementos relevantes después del H1
        all_elements = []
        for element in h1_element.find_all_next():
            if element.name in ['h1', 'h2', 'h3', 'p', 'div', 'span', 'li', 'ul', 'ol']:
                all_elements.append(element)
        
        current_h2 = None
        i = 0
        
        while i < len(all_elements):
            element = all_elements[i]
            
            # Si encontramos otro H1, detenemos
            if element.name == 'h1':
                break
                
            # Si es un H2, creamos nueva estructura
            elif element.name == 'h2':
                # Extraer texto después del H2
                texto_h2 = self._extract_text_between_headers(all_elements, i)
                
                h2_data = {
                    "titulo": element.get_text(strip=True),
                    "texto": texto_h2,
                    "h3": []
                }
                h1_data["h2"].append(h2_data)
                current_h2 = h2_data
                
            # Si es un H3 y tenemos un H2 actual
            elif element.name == 'h3' and current_h2:
                # Extraer texto después del H3
                texto_h3 = self._extract_text_between_headers(all_elements, i)
                
                h3_data = {
                    "titulo": element.get_text(strip=True),
                    "texto": texto_h3
                }
                current_h2["h3"].append(h3_data)
            
            i += 1
        
        return h1_data
    
    def _extract_text_after_element(self, element, soup) -> str:
        """Extrae texto limpio después de un elemento hasta el siguiente encabezado"""
        text_parts = []
        
        # Buscar en todos los elementos siguientes, no solo hermanos
        for next_elem in element.find_all_next():
            # Detenerse en el siguiente encabezado
            if next_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
                
            # Extraer texto de elementos relevantes
            if next_elem.name in ['p', 'div', 'span', 'li', 'td', 'th']:
                # Evitar elementos que ya hemos procesado como padres
                if any(parent in text_parts for parent in next_elem.parents):
                    continue
                    
                text = next_elem.get_text(strip=True)
                # Filtrar texto basura pero ser menos restrictivo
                if text and len(text) > 5 and not self._is_junk_text(text):
                    # Evitar duplicados
                    if text not in ' '.join(text_parts):
                        text_parts.append(text)
        
        # Unir y limpiar el texto
        full_text = ' '.join(text_parts)
        return self._clean_text(full_text)[:2000]  # Aumentar límite a 2000 caracteres
    
    def _extract_text_between_headers(self, elements, start_index) -> str:
        """Extrae texto entre encabezados desde una lista de elementos"""
        text_parts = []
        seen_texts = set()  # Para evitar duplicados
        
        for i in range(start_index + 1, len(elements)):
            element = elements[i]
            
            # Detenerse en el siguiente encabezado
            if element.name in ['h1', 'h2', 'h3']:
                break
                
            # Extraer texto de elementos relevantes
            if element.name in ['p', 'div', 'span', 'li', 'td', 'th']:
                text = element.get_text(strip=True)
                # Filtrar texto basura pero ser menos restrictivo
                if text and len(text) > 5 and not self._is_junk_text(text):
                    # Evitar duplicados exactos
                    if text not in seen_texts:
                        text_parts.append(text)
                        seen_texts.add(text)
        
        # Unir y limpiar el texto
        full_text = ' '.join(text_parts)
        return self._clean_text(full_text)[:2000]  # Aumentar límite a 2000 caracteres
    
    def _is_junk_text(self, text: str) -> bool:
        """Detecta si el texto es basura (código, URLs, etc.)"""
        # Patrones de texto basura
        junk_patterns = [
            r'^https?://',  # URLs
            r'^\w+\.\w+',   # Dominios
            r'^[{}\[\]<>]', # Código
            r'^\d+$',       # Solo números
            r'^[A-Z_]+$',   # Solo mayúsculas (constantes)
            r'function\s*\(', # JavaScript
            r'class\s*=',    # HTML
            r'style\s*=',    # CSS inline
        ]
        
        import re
        for pattern in junk_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        # Si tiene demasiados caracteres especiales
        special_chars = sum(1 for c in text if c in '{}[]<>()=;:')
        if special_chars > len(text) * 0.3:
            return True
            
        return False
    
    def _clean_text(self, text: str) -> str:
        """Limpia el texto eliminando espacios extras y caracteres no deseados"""
        import re
        # Eliminar múltiples espacios
        text = re.sub(r'\s+', ' ', text)
        # Eliminar saltos de línea múltiples
        text = re.sub(r'\n+', ' ', text)
        # Eliminar espacios al inicio y final
        text = text.strip()
        return text
