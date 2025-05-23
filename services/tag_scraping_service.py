# services/tag_scraping_service.py

import asyncio
from typing import List, Dict, Any, Optional
# 👇👇👇 CORRECCIÓN: Importamos TimeoutError en lugar de PlaywrightTimeoutError 👇👇👇
from playwright.async_api import async_playwright, Browser, Page, TimeoutError
import httpx
from bs4 import BeautifulSoup
import logging

# Configura un logger para este módulo
logger = logging.getLogger(__name__)

# --- Funciones de Parseo y Extracción ---

def extraer_texto_bajo(tag) -> str:
    """Extrae texto 'limpio' entre un tag y el siguiente Hx."""
    contenido = []
    for sibling in tag.find_next_siblings():
        if sibling.name and sibling.name.lower() in ["h1", "h2", "h3"]:
            break
        texto = sibling.get_text(" ", strip=True)
        if texto:
            contenido.append(texto)
    return " ".join(contenido)

def parse_html_content(html: str) -> dict:
    """Parsea el HTML usando BeautifulSoup para extraer Title, Desc y Hx."""
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()

    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        result["description"] = meta_tag["content"].strip()

    body = soup.body
    if not body:
        return result

    h1_element = body.find('h1')
    if not h1_element:
        return result

    current_h1 = {
        "titulo": h1_element.get_text(strip=True),
        "texto": extraer_texto_bajo(h1_element),
        "h2": []
    }

    for h2_element in h1_element.find_next_siblings('h2'):
        prev_h1 = h2_element.find_previous_sibling('h1')
        if prev_h1 != h1_element: break
        current_h2 = {
            "titulo": h2_element.get_text(strip=True),
            "texto": extraer_texto_bajo(h2_element),
            "h3": []
        }
        current_h1["h2"].append(current_h2)
        for h3_element in h2_element.find_next_siblings('h3'):
            prev_h2 = h3_element.find_previous_sibling('h2')
            prev_h1_for_h3 = h3_element.find_previous_sibling('h1')
            if prev_h1_for_h3 != h1_element or prev_h2 != h2_element: break
            current_h2["h3"].append({
                "titulo": h3_element.get_text(strip=True),
                "texto": extraer_texto_bajo(h3_element)
            })
    result["h1"] = current_h1
    return result

# --- Funciones de Scraping (httpx y Playwright) ---

async def scrape_tags_with_httpx(url: str) -> dict:
    """Intenta scrapear usando httpx."""
    resultado = {"url": url}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers=headers, timeout=15)
        resultado["status_code"] = response.status_code
        if response.status_code == 200:
            logger.info(f"httpx OK (200) para {url}")
            resultado.update(parse_html_content(response.text))
        else:
            logger.warning(f"httpx NO obtuvo 200 ({response.status_code}) para {url}.")
    except Exception as e:
        logger.error(f"Excepción con httpx para {url}: {e}.")
        resultado["status_code"] = "error_httpx"
        resultado["error"] = str(e)
    return resultado

async def scrape_with_playwright(url: str, browser: Browser) -> dict:
    """Scrapea usando Playwright."""
    resultado = {"url": url}
    page = None
    context = None
    try:
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.set_extra_http_headers({"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"})
        response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        html = await page.content()
        status = response.status if response else "error_playwright_no_response"
        resultado["status_code"] = status
        if response and 200 <= status < 300:
            logger.info(f"Playwright OK ({status}) para {url}")
            resultado.update(parse_html_content(html))
        elif response:
            logger.warning(f"Playwright NO obtuvo 2xx ({status}) para {url}")
            resultado["error"] = f"Playwright obtuvo status {status}"
        else:
            logger.error(f"Playwright NO obtuvo respuesta para {url}")
            resultado["error"] = "Playwright no obtuvo respuesta"
    # 👇👇👇 CORRECCIÓN: Usamos TimeoutError en lugar de PlaywrightTimeoutError 👇👇👇
    except TimeoutError:
         logger.error(f"Timeout de Playwright para {url}")
         resultado["status_code"] = "error_playwright_timeout"
         resultado["error"] = "Timeout"
    except Exception as e:
        logger.error(f"Excepción en Playwright para {url}: {e}")
        resultado["status_code"] = "error_playwright_exception"
        resultado["error"] = str(e)
    finally:
        if page: await page.close()
        if context: await context.close()
    return resultado

async def scrape_tags_as_tree(url: str, browser: Browser) -> dict:
    """Orquesta el intento httpx y el fallback Playwright."""
    resultado_httpx = await scrape_tags_with_httpx(url)
    if resultado_httpx.get("status_code") == 200 and "error" not in resultado_httpx:
        return resultado_httpx
    logger.info(f"Fallback a Playwright para {url} (httpx status: {resultado_httpx.get('status_code')})")
    return await scrape_with_playwright(url, browser)

# --- Clase de Servicio ---

class TagScrapingService:
    """Servicio para orquestar la extracción de etiquetas."""

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        """Extrae URLs de un item del JSON."""
        urls = []
        for key in ["urls", "resultados"]:
            for url_item in item.get(key, []):
                url = url_item if isinstance(url_item, str) else (url_item.get("url") if isinstance(url_item, dict) else None)
                if url: urls.append(url)
        return list(dict.fromkeys(urls))

    async def _process_urls_concurrent(
        self,
        urls: List[str],
        browser: Browser,
        max_concurrent: int,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Procesa URLs concurrentemente."""
        results = [None] * len(urls)
        semaphore = asyncio.Semaphore(max_concurrent)
        total = len(urls)
        processed_count = 0

        async def process_single_url(index: int, url: str):
            nonlocal processed_count
            async with semaphore:
                processed_count += 1
                logger.info(f"Procesando {url} ({processed_count}/{total})")
                if progress_callback:
                    progress_callback(f"Analizando [{processed_count}/{total}]: {url}", processed_count / total)
                try:
                    results[index] = await scrape_tags_as_tree(url, browser)
                except Exception as e:
                    logger.error(f"Error FATAL procesando {url}: {e}")
                    results[index] = {"url": url, "status_code": "error_fatal", "error": str(e)}
                logger.info(f"Finalizado {url} ({processed_count}/{total})")

        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        return results

    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Punto de entrada principal."""
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
            try:
                for item in data_list:
                    if not isinstance(item, dict): continue
                    context = {k: item.get(k, "") for k in ["busqueda", "idioma", "region", "dominio", "url_busqueda"]}
                    urls = self._extract_urls_from_item(item)
                    if urls:
                        results = await self._process_urls_concurrent(urls, browser, max_concurrent, progress_callback)
                        all_results.append({**context, "resultados": results})
            finally:
                await browser.close()
        return all_results
