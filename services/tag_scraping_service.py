"""
Servicio de Tag Scraping - Extracción de estructura HTML
"""
import asyncio
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser
import logging
import httpx # <--- AÑADIR
from bs4 import BeautifulSoup # <--- AÑADIR
from playwright.async_api import TimeoutError as PlaywrightTimeoutError # <--- AÑADIR

# --- INICIO: Lógica movida o importada de scraper_tags_tree.py ---
#    (Idealmente, esto estaría en su propio archivo e importado,
#     pero lo incluimos aquí para claridad o si prefieres tenerlo junto)

def extraer_texto_bajo(tag):
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
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    if soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()

    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        result["description"] = meta_tag["content"].strip()

    contenido = []
    current_h1 = {"titulo": "", "texto": "", "h2": []}
    current_h2 = None

    body = soup.body
    if not body:
        return result

    # Considerar solo elementos relevantes para evitar ruido
    elementos = body.find_all(['h1', 'h2', 'h3', 'p', 'div', 'span', 'li', 'td']) # O ajustar según necesidad

    # --- Lógica de Parseo Mejorada (Ejemplo) ---
    # Esta parte es compleja y puede necesitar ajustes finos.
    # La lógica original tenía algunos detalles a pulir.
    # Esta es una versión simplificada/revisada, puede necesitar más trabajo.
    
    h1_element = body.find('h1')
    if not h1_element:
        return result

    current_h1 = {
        "titulo": h1_element.get_text(strip=True),
        "texto": extraer_texto_bajo(h1_element), # Intenta extraer texto bajo H1
        "h2": []
    }

    for h2_element in h1_element.find_next_siblings('h2'):
        # Asegurarse de que este H2 no pertenece a un H1 posterior
        prev_h1 = h2_element.find_previous_sibling('h1')
        if prev_h1 != h1_element:
            break # Salió del scope del H1 actual

        current_h2 = {
            "titulo": h2_element.get_text(strip=True),
            "texto": extraer_texto_bajo(h2_element),
            "h3": []
        }
        current_h1["h2"].append(current_h2)

        for h3_element in h2_element.find_next_siblings('h3'):
            prev_h2 = h3_element.find_previous_sibling('h2')
            prev_h1_for_h3 = h3_element.find_previous_sibling('h1')

            if prev_h1_for_h3 != h1_element or prev_h2 != h2_element:
                 break # Salió del scope del H2 actual

            current_h2["h3"].append({
                "titulo": h3_element.get_text(strip=True),
                "texto": extraer_texto_bajo(h3_element)
            })
            
    result["h1"] = current_h1
    return result
    # --- FIN Lógica de Parseo Mejorada ---


async def scrape_tags_with_httpx(url: str) -> dict:
    resultado = {"url": url}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
    }
    try:
        # Añadir follow_redirects=True por si hay redirecciones
        async with httpx.AsyncClient(follow_redirects=True) as client:
             response = await client.get(url, headers=headers, timeout=10)
        resultado["status_code"] = response.status_code

        if response.status_code != 200:
            logger.warning(f"httpx falló para {url} con status {response.status_code}. Intentando Playwright...")
            return resultado # Devuelve para que la lógica principal sepa que debe usar Playwright

        resultado.update(parse_html_content(response.text))

    except Exception as e:
        logger.error(f"Error con httpx para {url}: {e}. Intentando Playwright...")
        resultado["status_code"] = "error_httpx" # Código específico para saber que falló httpx
        resultado["error"] = str(e)
    return resultado

async def scrape_with_playwright(url: str, browser) -> dict:
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

        response = await page.goto(url, timeout=60000, wait_until="domcontentloaded") # 'domcontentloaded' puede ser más rápido
        
        # Espera un poco más si es necesario, o busca un selector específico
        await page.wait_for_timeout(3000) # Aumentar un poco si es necesario

        html = await page.content()
        resultado["status_code"] = response.status if response else "error_playwright"
        
        # Solo parsea si el status es bueno (o si quieres parsear incluso si hay error)
        if response and response.status == 200:
             resultado.update(parse_html_content(html))
        elif response:
             resultado["error"] = f"Playwright obtuvo status {response.status}"
        else:
            resultado["error"] = "Playwright no obtuvo respuesta"


    except Exception as e:
        resultado["status_code"] = "error_playwright"
        resultado["error"] = str(e)
    finally:
        if page: await page.close()
        if context: await context.close()
    return resultado

async def scrape_tags_as_tree(url: str, browser) -> dict:
    """
    Intenta extraer la jerarquía h1→h2→h3 primero con httpx.
    Si falla o no es 200, recurre a Playwright como fallback.
    """
    # 🔹 Primer intento con httpx
    resultado_httpx = await scrape_tags_with_httpx(url)
    # Si httpx funcionó Y obtuvo status 200, lo devolvemos
    if resultado_httpx.get("status_code") == 200:
        return resultado_httpx

    # 🔸 Fallback con Playwright (si httpx falló o no dio 200)
    logger.info(f"Usando Playwright para {url}...")
    resultado_playwright = await scrape_with_playwright(url, browser)
    
    # Si Playwright falló pero httpx tenía *algo* (aunque no fuera 200),
    # podríamos devolver el de httpx para no perder la info del status code.
    # O priorizar siempre el de Playwright si se ejecutó.
    # Aquí, priorizamos Playwright si se usó.
    return resultado_playwright

# --- FIN: Lógica movida o importada ---


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
                    context = { # ... (tu extracción de contexto) ...
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
        # ... (tu código actual está bien) ...
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
        """Procesa múltiples URLs con límite de concurrencia"""
        results = [None] * len(urls)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single_url(index: int, url: str):
            async with semaphore: # <--- El semáforo limita aquí
                logger.info(f"Adquiriendo semáforo para {url} ({index+1}/{len(urls)})")
                if progress_callback:
                    progress_callback(f"Analizando {url}...")
                try:
                    # 👇👇👇 CAMBIO PRINCIPAL: Llamamos a la nueva lógica 👇👇👇
                    result = await scrape_tags_as_tree(url, browser)
                    results[index] = result
                except Exception as e:
                    logger.error(f"Error FATAL procesando {url}: {e}")
                    results[index] = {
                        "url": url, "status_code": "error_fatal", "error": str(e)
                    }
                finally:
                    logger.info(f"Liberando semáforo para {url}")
                    # Actualizar progreso aquí también si quieres saber cuándo termina
                    if progress_callback:
                       progress_callback(f"Finalizado {url} ({index+1}/{len(urls)})")


        tasks = [process_single_url(i, url) for i, url in enumerate(urls)]
        await asyncio.gather(*tasks)

        # Asegurarnos de que los resultados mantengan el orden original
        # Si 'results' se llena por índice, ya debería estar ordenado.
        return results

    # ⛔️ REMOVER: Ya no usamos estas funciones ⛔️
    # async def _scrape_single_url(self, url: str, browser: Browser) -> Dict[str, Any]: ...
    # async def _extract_heading_structure(self, page) -> Dict[str, Any]: ...
