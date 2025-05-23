# services/tag_scraping_service.py

import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, PlaywrightTimeoutError
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
        # Usamos ' ' como separador y strip=True para limpiar espacios
        texto = sibling.get_text(" ", strip=True)
        if texto:
            contenido.append(texto)
    return " ".join(contenido)

def parse_html_content(html: str) -> dict:
    """Parsea el HTML usando BeautifulSoup para extraer Title, Desc y Hx."""
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    # Extraer Título
    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()

    # Extraer Meta Descripción
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        result["description"] = meta_tag["content"].strip()

    # Extraer Estructura Hx (Solo desde el primer H1)
    body = soup.body
    if not body:
        return result

    h1_element = body.find('h1')
    if not h1_element:
        # Si no hay H1, al menos devolvemos title y description
        return result

    current_h1 = {
        "titulo": h1_element.get_text(strip=True),
        "texto": extraer_texto_bajo(h1_element),
        "h2": []
    }

    # Itera sobre los H2 que son hermanos *posteriores* al H1
    for h2_element in h1_element.find_next_siblings('h2'):
        # Verifica que este H2 no pertenece a un H1 posterior (importante)
        prev_h1 = h2_element.find_previous_sibling('h1')
        if prev_h1 != h1_element:
            break  # Si encontramos un H1 diferente, paramos

        current_h2 = {
            "titulo": h2_element.get_text(strip=True),
            "texto": extraer_texto_bajo(h2_element),
            "h3": []
        }
        current_h1["h2"].append(current_h2)

        # Itera sobre los H3 que son hermanos *posteriores* al H2
        for h3_element in h2_element.find_next_siblings('h3'):
            # Verifica que este H3 pertenece al H2 y H1 actual
            prev_h2 = h3_element.find_previous_sibling('h2')
            prev_h1_for_h3 = h3_element.find_previous_sibling('h1')

            if prev_h1_for_h3 != h1_element or prev_h2 != h2_element:
                break  # Si encontramos un H2 o H1 diferente, paramos

            current_h2["h3"].append({
                "titulo": h3_element.get_text(strip=True),
                "texto": extraer_texto_bajo(h3_element)
            })

    result["h1"] = current_h1
    return result

# --- Funciones de Scraping (httpx y Playwright) ---

async def scrape_tags_with_httpx(url: str) -> dict:
    """Intenta scrapear usando httpx (ligero y rápido)."""
    resultado = {"url": url}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36", # <-- ¡PON UN USER AGENT REALISTA!
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False) as client: # verify=False si tienes problemas SSL
            response = await client.get(url, headers=headers, timeout=15)
        resultado["status_code"] = response.status_code

        if response.status_code == 200:
            logger.info(f"httpx OK (200) para {url}")
            resultado.update(parse_html_content(response.text))
        else:
            logger.warning(f"httpx NO obtuvo 200 ({response.status_code}) para {url}. Se usará Playwright.")
            # No añadimos error, dejamos que Playwright lo intente

    except Exception as e:
        logger.error(f"Excepción con httpx para {url}: {e}. Se usará Playwright.")
        resultado["status_code"] = "error_httpx"
        resultado["error"] = str(e)
    return resultado

async def scrape_with_playwright(url: str, browser: Browser) -> dict:
    """Scrapea usando Playwright (más pesado pero maneja JS)."""
    resultado = {"url": url}
    page = None
    context = None
    try:
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36" # <-- ¡PON UN USER AGENT REALISTA!
        )
        page = await context.new_page()
        await page.set_extra_http_headers({"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"})

        response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        # Opcional: Pequeña espera o acciones para contenido dinámico
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

    except PlaywrightTimeoutError:
         logger.error(f"Timeout de Playwright para {url}")
         resultado["status_code"] = "error_playwright_timeout"
         resultado["error"] = "Timeout"
    except Exception as e:
        logger.error(f"Excepción en Playwright para {url}: {e}")
        resultado["status_code"] = "error_playwright_exception"
        resultado["error"] = str(e)
    finally:
        if page:
            try: await page.close()
            except Exception: pass
        if context:
            try: await context.close()
            except Exception: pass
    return resultado

async def scrape_tags_as_tree(url: str, browser: Browser) -> dict:
    """Función principal que orquesta el intento httpx y el fallback Playwright."""
    resultado_httpx = await scrape_tags_with_httpx(url)
    # Si httpx funcionó Y obtuvo status 200, lo devolvemos
    if resultado_httpx.get("status_code") == 200 and "error" not in resultado_httpx:
        return resultado_httpx

    # Si no, usamos Playwright
    logger.info(f"Fallback a Playwright para {url} (httpx status: {resultado_httpx.get('status_code')})")
    return await scrape_with_playwright(url, browser)

# --- Clase de Servicio ---

class TagScrapingService:
    """Servicio para orquestar la extracción de etiquetas de múltiples URLs."""

    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        """Extrae todas las URLs de un item del JSON (tu lógica original)."""
        urls = []
        # Buscar en campo 'urls'
        if "urls" in item:
            for url_item in item.get("urls", []):
                if isinstance(url_item, str):
                    urls.append(url_item)
                elif isinstance(url_item, dict) and "url" in url_item:
                    urls.append(url_item["url"])
        # Buscar en campo 'resultados'
        if "resultados" in item:
            for result in item.get("resultados", []):
                if isinstance(result, dict) and "url" in result:
                    urls.append(result["url"])
        # Devolver URLs únicas para evitar procesar la misma dos veces si aparece en ambos
        return list(dict.fromkeys(urls)) 

    async def _process_urls_concurrent(
        self,
        urls: List[str],
        browser: Browser,
        max_concurrent: int,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Procesa múltiples URLs con límite de concurrencia."""
        results = [None] * len(urls)
        semaphore = asyncio.Semaphore(max_concurrent)
        total = len(urls)
        processed_count = 0

        async def process_single_url(index: int, url: str):
            nonlocal processed_count
            async with semaphore:
                processed_count += 1
                logger.info(f"Adquiriendo semáforo para {url} ({processed_count}/{total})")
                if progress_callback:
                    # Pasamos el conteo y total al callback para la barra de progreso
                    progress_callback(f"Analizando [{processed_count}/{total}]: {url}", processed_count / total)
                
                try:
                    result = await scrape_tags_as_tree(url, browser)
                    results[index] = result
                except Exception as e:
                    logger.error(f"Error MUY GRAVE procesando {url}: {e}")
                    results[index] = {"url": url, "status_code": "error_fatal", "error": str(e)}
                
                logger.info(f"Liberando semáforo para {url}")
                # Opcional: Llamar de nuevo al callback para indicar fin
                # if progress_callback:
                #    progress_callback(f"Finalizado {url} ({processed_count}/{total})", processed_count / total)

        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)
        return results

    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Punto de entrada principal del servicio."""
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"] # Args comunes para Docker/Linux
            )
            try:
                for item in data_list:
                    if not isinstance(item, dict): continue
                    
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
                            urls, browser, max_concurrent, progress_callback
                        )
                        all_results.append({**context, "resultados": results})
            finally:
                await browser.close()
                logger.info("Navegador Playwright cerrado.")
        
        return all_results
