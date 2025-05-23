import json
import streamlit as st
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import httpx
from bs4 import BeautifulSoup
import logging

# --- Lógica de Scraping (Versión ASYNC Buena) ---
#    (La hemos traído aquí para tener todo en un solo lugar,
#     pero idealmente estaría en su propio módulo 'modules/utils/scraper_logic.py')

logger = logging.getLogger(__name__)

def extraer_texto_bajo(tag):
    contenido = []
    for sibling in tag.find_next_siblings():
        if sibling.name and sibling.name.lower() in ["h1", "h2", "h3"]:
            break
        texto = sibling.get_text(" ", strip=True)
        if texto:
            contenido.append(texto)
    return " ".join(contenido)

def parse_html_content(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = {}
    if soup.title and soup.title.string: result["title"] = soup.title.string.strip()
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"): result["description"] = meta_tag["content"].strip()

    h1_element = soup.body.find('h1') if soup.body else None
    if not h1_element: return result
    
    current_h1 = {"titulo": h1_element.get_text(strip=True), "texto": extraer_texto_bajo(h1_element), "h2": []}
    for h2_element in h1_element.find_next_siblings('h2'):
        prev_h1 = h2_element.find_previous_sibling('h1')
        if prev_h1 != h1_element: break
        current_h2 = {"titulo": h2_element.get_text(strip=True), "texto": extraer_texto_bajo(h2_element), "h3": []}
        current_h1["h2"].append(current_h2)
        for h3_element in h2_element.find_next_siblings('h3'):
            prev_h2 = h3_element.find_previous_sibling('h2')
            prev_h1_for_h3 = h3_element.find_previous_sibling('h1')
            if prev_h1_for_h3 != h1_element or prev_h2 != h2_element: break
            current_h2["h3"].append({"titulo": h3_element.get_text(strip=True), "texto": extraer_texto_bajo(h3_element)})
    result["h1"] = current_h1
    return result

async def scrape_tags_with_httpx(url: str) -> dict:
    resultado = {"url": url}
    headers = { "User-Agent": "...", "Accept-Language": "..." } # Tu User-Agent
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=10)
        resultado["status_code"] = response.status_code
        if response.status_code == 200:
            resultado.update(parse_html_content(response.text))
        else:
            logger.warning(f"httpx no obtuvo 200 ({response.status_code}) para {url}.")
    except Exception as e:
        logger.error(f"Error httpx para {url}: {e}.")
        resultado["status_code"] = "error_httpx"
        resultado["error"] = str(e)
    return resultado

async def scrape_with_playwright(url: str, browser) -> dict:
    resultado = {"url": url}
    page = None
    context = None
    try:
        context = await browser.new_context(ignore_https_errors=True, user_agent="...") # Tu User-Agent
        page = await context.new_page()
        await page.set_extra_http_headers({"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"})
        response = await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        html = await page.content()
        status = response.status if response else "error_playwright"
        resultado["status_code"] = status
        if response and 200 <= status < 300:
            resultado.update(parse_html_content(html))
        elif response:
            resultado["error"] = f"Playwright obtuvo status {status}"
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
    resultado_httpx = await scrape_tags_with_httpx(url)
    if resultado_httpx.get("status_code") == 200:
        return resultado_httpx
    return await scrape_with_playwright(url, browser)

# --- FIN Lógica de Scraping ---

# --- Módulos Utils (Asegúrate de que las rutas son correctas) ---
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta, obtener_contenido_archivo_drive,
    subir_json_a_drive, obtener_o_crear_subcarpeta
)
from modules.utils.mongo_utils import subir_a_mongodb
# --- Fin Módulos Utils ---


def render_scraping_etiquetas_url():
    st.session_state["_called_script"] = "scraping_etiquetas_url"
    st.title("🧬 Extraer estructura jerárquica (h1 → h2 → h3)")
    st.markdown("### 📁 Sube o selecciona un archivo JSON con URLs")

    # --- Lógica para cargar JSON (Tu código actual parece bien) ---
    fuente = st.radio("Selecciona fuente:", ["Desde Drive", "Desde ordenador"], horizontal=True)
    
    def procesar_json(crudo):
        try:
            return json.loads(crudo.decode("utf-8") if isinstance(crudo, bytes) else crudo)
        except Exception as e: st.error(f"❌ Error al procesar JSON: {e}"); return None

    # (Aquí va tu lógica para cargar desde Drive o PC - Mantenla como está)
    # ...
    # Asegúrate de que al final tienes 'datos_json' cargado.
    # --- Fin Lógica Carga ---

    # --- Lógica Principal de Procesamiento ---
    if "json_contenido" in st.session_state and "salida_json" not in st.session_state:
        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json: return

        iterable = datos_json if isinstance(datos_json, list) else [datos_json]
        salidas = []
        max_concurrentes = st.slider("🔁 Concurrencia máxima", 1, 10, 5)

        # Contenedores para el progreso
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        total_urls = sum(len(e.get("urls", []) + e.get("resultados", [])) for e in iterable)
        processed_count = 0

        async def run_processing():
            nonlocal processed_count # Para poder modificarla desde la subtarea
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                
                for entrada in iterable:
                    if not isinstance(entrada, dict): continue

                    contexto = {k: entrada.get(k, "") for k in ["busqueda", "idioma", "region", "dominio", "url_busqueda"]}
                    
                    urls_a_procesar = []
                    # Extracción de URLs (simplificada)
                    for key in ["urls", "resultados"]:
                        for item in entrada.get(key, []):
                            url = item if isinstance(item, str) else (item.get("url") if isinstance(item, dict) else None)
                            if url: urls_a_procesar.append(url)
                    
                    if not urls_a_procesar: continue

                    resultados_parciales = [None] * len(urls_a_procesar)
                    semaforo = asyncio.Semaphore(max_concurrentes)

                    async def procesar_una(i, url):
                        nonlocal processed_count
                        async with semaforo:
                            status_text.text(f"Analizando [{processed_count+1}/{total_urls}]: {url}")
                            try:
                                resultado = await scrape_tags_as_tree(url, browser)
                            except Exception as e:
                                resultado = {"url": url, "status_code": "error_app", "error": str(e)}
                            resultados_parciales[i] = resultado
                            processed_count += 1
                            progress_bar.progress(processed_count / total_urls)
                        return resultado # Devolvemos para que gather no sea None

                    tareas = [procesar_una(i, url) for i, url in enumerate(urls_a_procesar)]
                    await asyncio.gather(*tareas)
                    
                    salidas.append({**contexto, "resultados": resultados_parciales})
                
                await browser.close()
            status_text.success(f"✅ ¡Proceso completado! Se analizaron {total_urls} URLs.")

        # Ejecutar el proceso asíncrono
        asyncio.run(run_processing())

        st.session_state["salida_json"] = salidas
        base = st.session_state.get("json_nombre", "etiquetas.json")
        st.session_state["nombre_archivo_exportar"] = base.replace(".json", "_ALL.json")

    # --- Lógica de Exportación y Visualización ---
    if "salida_json" in st.session_state:
        salida = st.session_state["salida_json"]
        nombre_archivo = st.text_input("📄 Nombre para exportar:", value=st.session_state["nombre_archivo_exportar"])
        st.session_state["nombre_archivo_exportar"] = nombre_archivo

        # (Tu código de botones de exportación - Mantenlo como está)
        # ...
        
        st.subheader("📦 Resultados")
        # 👇👇👇 CAMBIO: Añadido expanded=True 👇👇👇
        st.json(salida, expanded=True) 

# --- Asegúrate de llamar a la función ---
# render_scraping_etiquetas_url() 
# (O como lo tengas estructurado en tu app multipágina)
