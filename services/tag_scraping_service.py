import asyncio
import time
import random
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
import httpx
from bs4 import BeautifulSoup
import logging
# from config import config # Asegúrate de que config existe

logger = logging.getLogger(__name__)

# <<<< NO HAY 'from services.tag_scraping_service import TagScrapingService' AQUÍ >>>>

class TagScrapingService:
    """Servicio optimizado para extraer estructura jerárquica de etiquetas HTML"""

    def __init__(self):
        self.http_client = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        ]
        self.successful_httpx_count = 0
        self.playwright_fallback_count = 0

    async def scrape_tags_from_json(self, json_data: Any, max_concurrent: int = 5, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []
        headers = {"User-Agent": random.choice(self.user_agents), "Accept": "text/html...", "Accept-Language": "es-ES..."}

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), headers=headers, follow_redirects=True, http2=True,
                                   limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)) as http_client:
            self.http_client = http_client
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"])
                try:
                    for item in data_list:
                        if not isinstance(item, dict): continue
                        context = { k: item.get(k, "") for k in ["busqueda", "idioma", "region", "dominio", "url_busqueda"] }
                        urls = self._extract_urls_from_item(item)
                        if urls:
                            results = await self._process_urls_concurrent(urls, browser, max_concurrent, progress_callback)
                            all_results.append({**context, "resultados": results})
                finally:
                    await browser.close()
                    self.http_client = None
        return all_results

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        urls = []
        for key in ["urls", "resultados"]:
            if key in item:
                for sub_item in item[key]:
                    if isinstance(sub_item, str): urls.append(sub_item)
                    elif isinstance(sub_item, dict) and "url" in sub_item: urls.append(sub_item["url"])
        return urls

    async def _process_urls_concurrent(self, urls: List[str], browser: Browser, max_concurrent: int, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        results = [None] * len(urls)
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0

        async def process_single_url(index: int, url: str):
            nonlocal completed_count
            async with semaphore:
                try:
                    if progress_callback: progress_callback(f"🔄 {completed_count}/{len(urls)} | {url[:50]}...")
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    result = await self._scrape_single_url(url, browser)
                    results[index] = result
                    completed_count += 1
                    if progress_callback: progress_callback(f"✅ {completed_count}/{len(urls)} | {result.get('method','?')} | {url[:50]}...")
                except Exception as e:
                    logger.error(f"Error _process_urls_concurrent {url}: {e}")
                    results[index] = {"url": url, "status_code": "error", "error": str(e)}
                    completed_count += 1
        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        return results

    async def _scrape_single_url(self, url: str, browser: Browser) -> Dict[str, Any]:
        start_time = time.time()
        try:
            self.http_client.headers["User-Agent"] = random.choice(self.user_agents)
            response = await self.http_client.get(url)
            if response.status_code == 200 and len(response.content) > 500: # Reducido un poco para probar
                result = await self._scrape_with_httpx(url, response, start_time)
                if result["h1"]:
                    self.successful_httpx_count += 1
                    return result
            logger.info(f"Fallback Playwright {url}")
        except Exception as e:
            logger.warning(f"httpx failed {url}: {e}, fallback...")
        self.playwright_fallback_count += 1
        return await self._scrape_with_playwright(url, browser, start_time)

    async def _scrape_with_httpx(self, url: str, response: httpx.Response, start_time: float) -> Dict[str, Any]:
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]): script.decompose()
        title = soup.find('title').text.strip() if soup.find('title') else ""
        h1_structure = self._extract_heading_structure_soup(soup)
        elapsed_time = time.time() - start_time
        return {"url": url, "status_code": response.status_code, "title": title, "h1": h1_structure, "scraping_time": elapsed_time, "method": "httpx"}

    def _extract_heading_structure_soup(self, soup: BeautifulSoup) -> Dict[str, Any]:
        h1 = soup.find('h1')
        if not h1: return {}
        result = {"titulo": h1.text.strip(), "level": "h1", "h2": []}
        current = h1.find_next_sibling()
        current_h2 = None
        while current:
            if current.name == 'h1': break
