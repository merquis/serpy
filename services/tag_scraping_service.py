import logging
from typing import List, Dict, Any, Optional, Callable
import asyncio
from rebrowser_playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from services.utils.httpx_service import HttpxService, create_stealth_httpx_config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML: primero httpx, si falla rebrowser-playwright"""

    def __init__(self):
        self.httpx_config = create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)

    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
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
            resultados = await self._scrape_urls_with_fallback(urls, max_concurrent, progress_callback)
            all_results.append({**context, "resultados": resultados})

        return all_results

    async def _scrape_urls_with_fallback(
        self,
        urls: List[str],
        max_concurrent: int,
        progress_callback: Optional[Callable]
    ) -> List[Dict[str, Any]]:
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        total = len(urls)
        completed = 0
        active = 0

        async def process_url(url: str, idx: int):
            nonlocal completed, active
            async with semaphore:
                active += 1
                if progress_callback:
                    progress_callback({
                        "current_url": url,
                        "completed": completed,
                        "total": total,
                        "active": active,
                        "remaining": total - completed
                    })
                # 1. Intentar con httpx
                try:
                    result, html = await self.httpx_service.get_html(url)
                    if result.get("success") and html:
                        soup = BeautifulSoup(html, "html.parser")
                        title = soup.title.string.strip() if soup.title else ""
                        meta = soup.find("meta", attrs={"name": "description"})
                        description = meta["content"].strip() if meta and meta.has_attr("content") else ""
                        h1_structure = self._extract_h1_structure(soup)
                        completed += 1
                        active -= 1
                        if progress_callback:
                            progress_callback({
                                "current_url": url,
                                "completed": completed,
                                "total": total,
                                "active": active,
                                "remaining": total - completed
                            })
                        return {
                            "url": url,
                            "status_code": 200,
                            "title": title,
                            "description": description,
                            "h1": h1_structure,
                            "method": "httpx"
                        }
                except Exception as e:
                    logger.warning(f"Error httpx para {url}: {e}")

                # 2. Si httpx falla, usar rebrowser-playwright
                try:
                    async with async_playwright() as p:
                        browser = await p.chromium.launch()
                        page = await browser.new_page()
                        await page.goto(url)
                        html = await page.content()
                        await browser.close()
                    soup = BeautifulSoup(html, "html.parser")
                    title = soup.title.string.strip() if soup.title else ""
                    meta = soup.find("meta", attrs={"name": "description"})
                    description = meta["content"].strip() if meta and meta.has_attr("content") else ""
                    h1_structure = self._extract_h1_structure(soup)
                    completed += 1
                    active -= 1
                    if progress_callback:
                        progress_callback({
                            "current_url": url,
                            "completed": completed,
                            "total": total,
                            "active": active,
                            "remaining": total - completed
                        })
                    return {
                        "url": url,
                        "status_code": 200,
                        "title": title,
                        "description": description,
                        "h1": h1_structure,
                        "method": "rebrowser"
                    }
                except Exception as e:
                    logger.error(f"Error rebrowser-playwright para {url}: {e}")
                    completed += 1
                    active -= 1
                    if progress_callback:
                        progress_callback({
                            "current_url": url,
                            "completed": completed,
                            "total": total,
                            "active": active,
                            "remaining": total - completed
                        })
                    return {
                        "url": url,
                        "status_code": "error",
                        "error": str(e),
                        "method": "rebrowser"
                    }

        tasks = [process_url(url, idx) for idx, url in enumerate(urls)]
        results = await asyncio.gather(*tasks)
        return results

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
        h1_element = soup.find('h1')
        if not h1_element:
            return {}
        h1_data = {
            "titulo": h1_element.get_text(strip=True),
            "texto": self._extract_text_after_element(h1_element, soup),
            "h2": []
        }
        all_elements = []
        for element in h1_element.find_all_next():
            if element.name in ['h1', 'h2', 'h3', 'p', 'div', 'span', 'li', 'ul', 'ol']:
                all_elements.append(element)
        current_h2 = None
        i = 0
        while i < len(all_elements):
            element = all_elements[i]
            if element.name == 'h1':
                break
            elif element.name == 'h2':
                texto_h2 = self._extract_text_between_headers(all_elements, i)
                h2_data = {
                    "titulo": element.get_text(strip=True),
                    "texto": texto_h2,
                    "h3": []
                }
                h1_data["h2"].append(h2_data)
                current_h2 = h2_data
            elif element.name == 'h3' and current_h2:
                texto_h3 = self._extract_text_between_headers(all_elements, i)
                h3_data = {
                    "titulo": element.get_text(strip=True),
                    "texto": texto_h3
                }
                current_h2["h3"].append(h3_data)
            i += 1
        return h1_data

    def _extract_text_after_element(self, element, soup) -> str:
        text_parts = []
        for next_elem in element.find_all_next():
            if next_elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            if next_elem.name in ['p', 'div', 'span', 'li', 'td', 'th']:
                if any(parent in text_parts for parent in next_elem.parents):
                    continue
                text = next_elem.get_text(strip=True)
                if text and len(text) > 5 and not self._is_junk_text(text):
                    if text not in ' '.join(text_parts):
                        text_parts.append(text)
        full_text = ' '.join(text_parts)
        return self._clean_text(full_text)[:2000]

    def _extract_text_between_headers(self, elements, start_index) -> str:
        text_parts = []
        seen_texts = set()
        for i in range(start_index + 1, len(elements)):
            element = elements[i]
            if element.name in ['h1', 'h2', 'h3']:
                break
            if element.name in ['p', 'div', 'span', 'li', 'td', 'th']:
                text = element.get_text(strip=True)
                if text and len(text) > 5 and not self._is_junk_text(text):
                    if text not in seen_texts:
                        text_parts.append(text)
                        seen_texts.add(text)
        full_text = ' '.join(text_parts)
        return self._clean_text(full_text)[:2000]

    def _is_junk_text(self, text: str) -> bool:
        junk_patterns = [
            r'^https?://',
            r'^\w+\.\w+',
            r'^[{}\[\]<>]',
            r'^\d+$',
            r'^[A-Z_]+$',
            r'function\s*\(',
            r'class\s*=',
            r'style\s*='
        ]
        import re
        for pattern in junk_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        special_chars = sum(1 for c in text if c in '{}[]<>()=;:')
        if special_chars > len(text) * 0.3:
            return True
        return False

    def _clean_text(self, text: str) -> str:
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', ' ', text)
        text = text.strip()
        return text
