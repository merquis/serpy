"""
Servicio de Tag Scraping - Extracción de estructura HTML
"""
import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser
import logging
from config import config
from services.scraper_tags_tree import scrape_tags_as_tree

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""

    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrae la estructura de etiquetas de URLs contenidas en JSON

        Args:
            json_data: Datos JSON con URLs (puede ser dict o list)
            max_concurrent: Número máximo de scrapers concurrentes
            progress_callback: Función callback para actualizar progreso

        Returns:
            Lista de resultados con estructura de etiquetas
        """
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

            try:
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

                    if urls:
                        results = await self._process_urls_concurrent(
                            urls,
                            browser,
                            max_concurrent,
                            progress_callback
                        )

                        all_results.append({
                            **context,
                            "resultados": results
                        })

            finally:
                await browser.close()

        return all_results

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        urls = []
        if "urls" in item:
            for url_item in item["urls"]:
                if isinstance(url_item, str):
                    urls.append(url_item)
                elif isinstance(url_item, dict) and "url" in url_item:
                    urls.append(url_item["url"])
        if "resultados" in item:
            for result in item["resultados"]:
                if isinstance(result, dict) and "url" in result:
                    urls.append(result["url"])
        return urls

    async def _process_urls_concurrent(
        self,
        urls: List[str],
        browser: Browser,
        max_concurrent: int,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        results = [None] * len(urls)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single_url(index: int, url: str):
            async with semaphore:
                try:
                    if progress_callback:
                        progress_callback(f"Analizando {url}...")
                    result = await scrape_tags_as_tree(url, browser)
                    results[index] = result
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    results[index] = {
                        "url": url,
                        "status_code": "error",
                        "error": str(e)
                    }

        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        return results
