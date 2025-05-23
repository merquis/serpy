import asyncio
import json
import datetime
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

class BookingScrapingService:
    """Servicio para extraer datos de hoteles de Booking.com"""

    async def scrape_hotels(
        self,
        urls: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            try:
                tasks = []
                for i, url in enumerate(urls):
                    if progress_callback: progress_callback(f"Procesando {i+1}/{len(urls)}: {url}")
                    tasks.append(self._scrape_single_hotel(url, browser))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                final_results = []
                for i, res in enumerate(results):
                    url = urls[i]
                    if isinstance(res, Exception):
                        final_results.append({"error": "Fallo_Excepcion_Gather", "url_original": url, "details": str(res)})
                    elif isinstance(res, dict):
                        final_results.append(res)
                    else:
                        final_results.append({"error": "Fallo_ResultadoInesperado", "url_original": url, "details": str(res)})
                return final_results
            finally:
                await browser.close()

    async def _scrape_single_hotel(self, url: str, browser: Browser) -> Dict[str, Any]:
        context = page = None
        try:
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            })
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await page.wait_for_selector("#hp_hotel_name, h1", timeout=15000)
            html = await page.content()
            if not html: return {"error": "Fallo_HTML_Vacio", "url_original": url, "details": "No se obtuvo contenido HTML"}
            soup = BeautifulSoup(html, "html.parser")
            return self._parse_hotel_html(soup, url)
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {"error": f"Fallo_Excepcion_{type(e).__name__}", "url_original": url, "details": str(e)}
        finally:
            if page: await page.close()
            if context: await context.close()

    def _parse_hotel_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        data_extraida = self._extract_structured_data(soup)
        imagenes = self._extract_images(soup)
        servicios = self._extract_facilities(soup)
        h1_tag = soup.find("h1")
        titulo_h1 = h1_tag.get_text(strip=True) if h1_tag else ""
        h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
        address_info = data_extraida.get("address", {})
        rating_info = data_extraida.get("aggregateRating", {})
        return {
            "url_original": url, "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "nombre_alojamiento": data_extraida.get("name", titulo_h1), "direccion": address_info.get("streetAddress"),
            "valoracion_global": rating_info.get("ratingValue"), "numero_opiniones": rating_info.get("reviewCount"),
            "titulo_h1": titulo_h1, "subtitulos_h2": h2s, "servicios_principales": servicios, "imagenes": imagenes,
        }

    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if script.string:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict) and data.get("@type") == "Hotel": return data
                    except: continue
        except: pass
        return {}

    def _extract_images(self, soup: BeautifulSoup, max_images: int = 15) -> List[str]:
        imagenes, found_urls = [], set()
        try:
            for img_tag in soup.find_all("img"):
                src = img_tag.get("src")
                if src and "xdata/images/hotel/" in src and ".jpg" in src and src not in found_urls and len(imagenes) < max_images:
                    src = re.sub(r"/max[^/]+/", "/max1024x768/", src).split("&o=")[0]
                    imagenes.append(src)
                    found_urls.add(src)
        except Exception as e: logger.error(f"Error extrayendo imágenes: {e}")
        return imagenes

    def _extract_facilities(self, soup: BeautifulSoup) -> List[str]:
        servicios_set = set()
        try:
            classes = ["hotel-facilities__list", "facilitiesChecklistSection", "hp_desc_important_facilities", "bui-list__description", "db29ecfbe2"]
            for class_name in classes:
                for container in soup.find_all(class_=class_name):
                    for item in container.find_all(['li', 'span', 'div']):
                        texto = item.get_text(strip=True)
                        if texto and len(texto) > 3: servicios_set.add(texto)
        except Exception as e: logger.error(f"Error extrayendo servicios: {e}")
        return sorted(list(servicios_set))
