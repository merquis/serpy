import asyncio
import time
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
import httpx
from bs4 import BeautifulSoup
import logging
from config import config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""

    def __init__(self):
        self.http_client = None

    async def scrape_tags_from_json(self, json_data: Any, max_concurrent: int = 5, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []

        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as http_client:
            self.http_client = http_client

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
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
                            results = await self._process_urls_concurrent(urls, browser, max_concurrent, progress_callback)
                            all_results.append({**context, "resultados": results})
                finally:
                    await browser.close()
                    self.http_client = None

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

    async def _process_urls_concurrent(self, urls: List[str], browser: Browser, max_concurrent: int, progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        results = [None] * len(urls)
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0
        active_tasks = set()

        async def process_single_url(index: int, url: str):
            nonlocal completed_count
            async with semaphore:
                try:
                    active_tasks.add(url)
                    if progress_callback:
                        progress_callback(f"🔄 Procesando {len(active_tasks)}/{max_concurrent} tareas concurrentes | Completadas: {completed_count}/{len(urls)} | Actual: {url[:50]}...")
                    result = await self._scrape_single_url(url, browser)
                    results[index] = result
                    completed_count += 1
                    active_tasks.discard(url)
                    if progress_callback:
                        method = result.get("method", "unknown")
                        progress_callback(f"✅ Completadas: {completed_count}/{len(urls)} | Activas: {len(active_tasks)} | Método: {method} | URL: {url[:50]}...")
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    results[index] = {"url": url, "status_code": "error", "error": str(e)}
                    completed_count += 1
                    active_tasks.discard(url)

        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        return results

    async def _scrape_single_url(self, url: str, browser: Browser) -> Dict[str, Any]:
        start_time = time.time()
        try:
            response = await self.http_client.get(url, follow_redirects=True)
            if response.status_code == 200:
                result = await self._scrape_with_httpx(url, response, start_time)
                if result["h1"]:
                    return result
            logger.info(f"Falling back to Playwright for {url} (status: {response.status_code})")
        except Exception as e:
            logger.warning(f"httpx failed for {url}: {e}, falling back to Playwright")
        return await self._scrape_with_playwright(url, browser, start_time)

    async def _scrape_with_httpx(self, url: str, response: httpx.Response, start_time: float) -> Dict[str, Any]:
        soup = BeautifulSoup(response.content, 'html.parser')
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else ""
        h1_structure = self._extract_heading_structure_soup(soup)
        elapsed_time = time.time() - start_time
        logger.info(f"Scraped {url} with httpx in {elapsed_time:.2f}s")
        return {
            "url": url,
            "status_code": response.status_code,
            "title": title,
            "h1": h1_structure,
            "scraping_time": elapsed_time,
            "method": "httpx"
        }

    def _extract_heading_structure_soup(self, soup: BeautifulSoup) -> Dict[str, Any]:
        h1 = soup.find('h1')
        if not h1:
            return {}
        result = {"titulo": h1.text.strip(), "level": "h1", "h2": []}
        current = h1.find_next_sibling()
        current_h2 = None
        while current:
            if current.name == 'h1':
                break
            elif current.name == 'h2':
                current_h2 = {"titulo": current.text.strip(), "level": "h2", "h3": []}
                result["h2"].append(current_h2)
            elif current.name == 'h3' and current_h2:
                current_h2["h3"].append({"titulo": current.text.strip(), "level": "h3"})
            current = current.find_next_sibling()
        return result

    async def _scrape_with_playwright(self, url: str, browser: Browser, start_time: float) -> Dict[str, Any]:
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        try:
            page.set_default_timeout(20000)
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            })
            response = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            status_code = response.status if response else 0
            await page.wait_for_timeout(1000)
            title = await page.title()
            h1_structure = await self._extract_heading_structure_playwright(page)
            elapsed_time = time.time() - start_time
            logger.info(f"Scraped {url} with Playwright in {elapsed_time:.2f}s")
            return {
                "url": url,
                "status_code": status_code,
                "title": title,
                "h1": h1_structure,
                "scraping_time": elapsed_time,
                "method": "playwright"
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error scraping {url} with Playwright after {elapsed_time:.2f}s: {e}")
            raise
        finally:
            await page.close()
            await context.close()

    async def _extract_heading_structure_playwright(self, page: Page) -> Dict[str, Any]:
        return await page.evaluate("""
            () => {
                const h1 = document.querySelector('h1');
                if (!h1) return {};
                const result = { titulo: h1.textContent.trim(), level: 'h1', h2: [] };
                let currentElement = h1.nextElementSibling;
                let currentH2 = null;
                while (currentElement) {
                    if (currentElement.tagName === 'H1') {
                        break;
                    } else if (currentElement.tagName === 'H2') {
                        currentH2 = { titulo: currentElement.textContent.trim(), level: 'h2', h3: [] };
                        result.h2.push(currentH2);
                    } else if (currentElement.tagName === 'H3' && currentH2) {
                        currentH2.h3.push({ titulo: currentElement.textContent.trim(), level: 'h3' });
                    }
                    currentElement = currentElement.nextElementSibling;
                }
                return result;
            }
        """)
