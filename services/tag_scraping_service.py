import logging
from typing import List, Dict, Any, Optional, Callable
from services.utils.httpx_service import HttpxService, create_stealth_httpx_config
from services.utils.playwright_service import PlaywrightService, PlaywrightConfig
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""

    def __init__(self):
        self.httpx_config = create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
        self.playwright_config = PlaywrightConfig()
        self.playwright_service = PlaywrightService(self.playwright_config)

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
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    title = soup.title.string.strip() if soup.title else ""
                    meta = soup.find("meta", attrs={"name": "description"})
                    description = meta["content"].strip() if meta and meta.has_attr("content") else ""
                    h1_structure = self._extract_h1_structure(soup)

                    if not h1_structure or not h1_structure.get("titulo"):
                        return {
                            "error": "Sin_headers_httpx",
                            "url": url,
                            "status_code": 200,
                            "details": "No se detectaron encabezados con httpx",
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
                playwright_service=self.playwright_service,
                config=self.httpx_config,
                playwright_config=self.playwright_config,
                max_concurrent=max_concurrent,
                progress_callback=progress_callback
            )

            all_results.append({**context, "resultados": results})

        return all_results

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
        h1 = soup.find("h1")
        if not h1:
            return {}

        h1_data = {
            "titulo": h1.get_text(strip=True),
            "level": "h1",
            "h2": []
        }

        current = h1.find_next_sibling()
        current_h2 = None

        while current:
            if current.name == "h1":
                break
            elif current.name == "h2":
                h2_data = {
                    "titulo": current.get_text(strip=True),
                    "level": "h2",
                    "h3": []
                }
                h1_data["h2"].append(h2_data)
                current_h2 = h2_data
            elif current.name == "h3" and current_h2:
                h3_data = {
                    "titulo": current.get_text(strip=True),
                    "level": "h3"
                }
                current_h2["h3"].append(h3_data)
            current = current.find_next_sibling()

        return h1_data
