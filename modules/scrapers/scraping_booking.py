# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import json
import datetime
from urllib.parse import urlparse, parse_qs
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta # Asegúrate que esto no use st.session_state si se llama desde async

# ════════════════════════════════════════════════════
# 🛠️ Helper para obtener configuración de proxy
# ════════════════════════════════════════════════════
def get_proxy_settings():
    try:
        proxy_conf = st.secrets["brightdata_booking"]
        return {
            "server": f"http://{proxy_conf['host']}:{proxy_conf['port']}",
            "username": proxy_conf["username"],
            "password": proxy_conf["password"]
        }
    except KeyError as e:
        st.warning(f"⚠️ Falta la clave del proxy en st.secrets: {e}. Se continuará sin proxy.")
        print(f"Error al leer secretos del proxy: Falta la clave {e}")
        return None
    except Exception as e:
        st.warning(f"⚠️ Error al leer la configuración del proxy: {e}. Se continuará sin proxy.")
        print(f"Error inesperado al leer secretos del proxy: {e}")
        return None

# ════════════════════════════════════════════════════
# 📅 Función de scraping Booking usando Playwright + BrightData
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance=None):
    """
    Extrae datos de una URL de Booking.com.
    Puede usar una instancia de navegador existente o crear una nueva.
    """
    html = ""
    # Si no se pasa una instancia de navegador, creamos una para esta única ejecución.
    # Esto es menos eficiente para múltiples URLs pero permite flexibilidad.
    close_browser_on_finish = False
    current_p = None # Para manejar el contexto de playwright si se crea aquí

    try:
        if not browser_instance:
            close_browser_on_finish = True
            current_p = await async_playwright().start()
            proxy_config = get_proxy_settings() # Lee los settings aquí si el navegador se crea aquí
            browser_instance = await current_p.chromium.launch(
                headless=True,
                proxy=proxy_config
            )

        page = await browser_instance.new_page()
        # Opcional: Añadir cabeceras para parecer un navegador más real
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        await page.goto(url, timeout=90000, wait_until="domcontentloaded") # Aumentar timeout y esperar a que el DOM esté listo

        # Espera dinámica (ejemplo, esperar a que el script JSON-LD del hotel esté presente)
        try:
            await page.wait_for_selector('script[type="application/ld+json"]', timeout=20000)
        except PlaywrightTimeoutError:
            print(f"Timeout esperando selector clave (JSON-LD) en {url}. Se continuará con el HTML disponible.")
            # Podrías añadir un st.warning aquí si tienes acceso a Streamlit desde el contexto async
            # (lo cual no es directo si esto se ejecuta en un bucle asyncio.gather)

        # Pequeña espera adicional para contenido JS muy tardío, si es estrictamente necesario.
        # await page.wait_for_timeout(1000) # Reducir o eliminar si es posible

        html = await page.content()
        await page.close()

    except PlaywrightTimeoutError as e:
        print(f"Timeout general de Playwright para {url}: {e}")
        return {"error": "Timeout de Playwright", "url": url, "details": str(e)}, ""
    except Exception as e:
        print(f"Error de Playwright o de red para {url}: {e}")
        return {"error": "Error de Playwright/Red", "url": url, "details": str(e)}, ""
    finally:
        if close_browser_on_finish and browser_instance:
            await browser_instance.close()
        if close_browser_on_finish and current_p:
            await current_p.stop()


    if not html:
        return {"error": "No se pudo obtener HTML", "url": url}, ""

    # --- Parsing con BeautifulSoup ---
    soup = BeautifulSoup(html, "html.parser")

    # Parsear parámetros de la URL
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    group_adults = query_params.get('group_adults', ['2'])[0]
    group_children = query_params.get('group_children', ['0'])[0]
    no_rooms = query_params.get('no_rooms', ['1'])[0]
    dest_type = query_params.get('dest_type', ['city'])[0]

    # Inicializar variables
    data_extraida = {}
    imagenes_secundarias = []
    servicios = []

    # Extraer JSON-LD principal
    try:
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string)
                    # A veces el JSON-LD es una lista de diccionarios
                    if isinstance(data_json, list):
                        for item in data_json:
                            if isinstance(item, dict) and item.get("@type") == "Hotel":
                                data_extraida = item
                                break
                        if data_extraida: break # Salir del bucle principal si se encontró
                    elif isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                        data_extraida = data_json
                        break
                except json.JSONDecodeError as je:
                    print(f"Error decodificando JSON-LD en {url}: {je} - Contenido: {script.string[:100]}...")
                except Exception as e_json:
                    print(f"Error procesando script JSON-LD en {url}: {e_json}")
    except Exception as e_find_ld:
        print(f"Error buscando scripts JSON-LD en {url}: {e_find_ld}")


    # Extraer imágenes desde JSON interno
    try:
        scripts_json = soup.find_all('script', type='application/json')
        for script in scripts_json:
            if script.string and 'large_url' in script.string: # Comprobación rápida
                try:
                    data_json = json.loads(script.string)
                    stack = [data_json]
                    while stack and len(imagenes_secundarias) < 10: # Limitar a 10 imágenes
                        current = stack.pop()
                        if isinstance(current, dict):
                            for k, v in current.items():
                                if k == 'large_url' and isinstance(v, str) and v.startswith("https://cf.bstatic.com/xdata/images/hotel/max1024x768/"):
                                    if v not in imagenes_secundarias:
                                        imagenes_secundarias.append(v)
                                else: # Si no es la URL, pero es un dict o list, añadir al stack
                                    if isinstance(v, (dict, list)):
                                        stack.append(v)
                        elif isinstance(current, list):
                            for item in current: # Extender con los items de la lista
                                if isinstance(item, (dict, list)):
                                    stack.append(item)
                except json.JSONDecodeError as je:
                    print(f"Error decodificando script JSON (imágenes) en {url}: {je} - Contenido: {script.string[:100]}...")
                except Exception as e_img_json:
                    print(f"Error procesando script JSON (imágenes) en {url}: {e_img_json}")
    except Exception as e_find_json_img:
         print(f"Error buscando scripts JSON (imágenes) en {url}: {e_find_json_img}")


    # Extraer servicios del HTML
    try:
        svc_elements = soup.find_all('div', class_="bui-list__description")
        for svc in svc_elements:
            texto = svc.get_text(strip=True)
            if texto and texto not in servicios: servicios.append(texto)

        if not servicios: # Fallback
            svc_elements_li = soup.find_all('li', class_="hp_desc_important_facilities")
            for svc_li in svc_elements_li:
                texto = svc_li.get_text(strip=True)
                if texto and texto not in servicios: servicios.append(texto)
    except Exception as e_svc:
        print(f"Error extrayendo servicios en {url}: {e_svc}")


    # Mapear resultado
    resultado = {
        "url_original": url, # Útil para referencia
        "checkin": datetime.date.today().strftime("%Y-%m-%d"),
        "checkout": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "group_adults": group_adults,
        "group_children": group_children,
        "no_rooms": no_rooms,
        "dest_type": dest_type,
        "nombre_alojamiento": data_extraida.get("name"), # Usar .get() para evitar KeyErrors
        "direccion": data_extraida.get("address", {}).get("streetAddress"),
        "codigo_postal": data_extraida.get("address", {}).get("postalCode"),
        "ciudad": data_extraida.get("address", {}).get("addressLocality"),
        "pais": data_extraida.get("address", {}).get("addressCountry"),
        "tipo_alojamiento": data_extraida.get("@type"),
        "slogan_principal": None, # Requeriría selector específico
        "descripcion_corta": data_extraida.get("description"),
        "estrellas": data_extraida.get("starRating", {}).get("ratingValue") if data_extraida.get("starRating") else None, # Del JSON-LD
        "precio_noche": data_extraida.get("priceRange"), # A menudo el JSON-LD tiene un priceRange, no un precio exacto por noche.
        "alojamiento_destacado": None,
        "isla_relacionada": None,
        "frases_destacadas": [],
        "servicios": list(set(servicios)), # Eliminar duplicados
        # Para valoraciones detalladas, se necesitarían selectores específicos del HTML
        "valoracion_limpieza": None,
        "valoracion_confort": None,
        "valoracion_ubicacion": None,
        "valoracion_instalaciones_servicios": None, # Corregido nombre (sin '_')
        "valoracion_personal": None,
        "valoracion_calidad_precio": None,
        "valoracion_wifi": None,
        "valoracion_global": data_extraida.get("aggregateRating", {}).get("ratingValue"),
        "numero_opiniones": data_extraida.get("aggregateRating", {}).get("reviewCount"),
        "imagenes": imagenes_secundarias,
        "enlace_afiliado": url, # Es la URL original que podría tener tu tag de afiliado
        "sitio_web_oficial": None, # Raro que Booking lo ponga
        "titulo_h1": soup.find("h1").get_text(strip=True) if soup.find("h1") else None,
        "bloques_contenido_h2": [h2.get_text(strip=True) for h2 in soup.find_all("h2")],
    }
    return resultado, html

# ════════════════════════════════════════════════════
# 🎯 Interfaz Streamlit
# ════════════════════════════════════════════════════

# Wrapper síncrono para una sola URL (usado si no se procesan en lote)
def obtener_datos_booking_sync(url_sync):
    return asyncio.run(obtener_datos_booking_playwright(url_sync))


async def procesar_urls_en_lote(urls_a_procesar):
    tasks_results = []
    proxy_config = get_proxy_settings() # Obtener config del proxy una vez

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_config # Aplicar proxy a la instancia del navegador
        )
        try:
            tasks = [obtener_datos_booking_playwright(u, browser) for u in urls_a_procesar]
            # return_exceptions=True para que un error en una tarea no detenga las demás
            tasks_results_with_html = await asyncio.gather(*tasks, return_exceptions=True)

            # Procesar resultados y separar datos de HTML
            for res_or_exc in tasks_results_with_html:
                if isinstance(res_or_exc, Exception):
                    st.error(f"Error en una tarea de scraping: {res_or_exc}")
                    tasks_results.append({"error": "Excepción en asyncio.gather", "details": str(res_or_exc)})
                    # Podrías intentar guardar el último HTML exitoso o no guardar ninguno en este caso
                elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                    resultado_item, html_content_item = res_or_exc
                    tasks_results.append(resultado_item)
                    if resultado_item and not resultado_item.get("error"): # Si no hubo error en el scraping de esa URL
                        st.session_state.last_successful_html_content = html_content_item
                else: # Resultado inesperado
                    st.warning(f"Resultado inesperado de tarea de scraping: {res_or_exc}")
                    tasks_results.append({"error": "Resultado inesperado", "details": str(res_or_exc)})

        except Exception as e_browser:
            st.error(f"Error al gestionar el navegador o las tareas en lote: {e_browser}")
            # Añadir error para todas las URLs si el navegador falla catastróficamente
            for u_err in urls_a_procesar:
                 tasks_results.append({"error": "Fallo general del navegador", "url": u_err, "details": str(e_browser)})
        finally:
            if browser:
                await browser.close()
    return tasks_results


def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []
    if "last_successful_html_content" not in st.session_state: # Para guardar el HTML de la última URL exitosa
        st.session_state.last_successful_html_content = ""


    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles", key="buscar_hoteles_booking")

    if st.session_state.resultados_json:
        nombre_archivo = f"datos_hoteles_booking_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        # Filtrar resultados que no sean errores antes de volcar a JSON
        resultados_validos = [r for r in st.session_state.resultados_json if r and not r.get("error")]
        if resultados_validos:
            contenido_json = json.dumps(resultados_validos, ensure_ascii=False, indent=2).encode("utf-8")
            with col2:
                st.download_button(
                    label="⬇️ Exportar JSON",
                    data=contenido_json,
                    file_name=nombre_archivo,
                    mime="application/json",
                    key="descargar_json"
                )
            with col3:
                subir_a_drive_btn = st.button("☁️ Subir a Google Drive", key="subir_drive_booking")
                if subir_a_drive_btn:
                    with st.spinner("☁️ Subiendo JSON a Google Drive (cuenta de servicio)..."):
                        # Asumo que drive_utils no usa st.session_state de forma que cause problemas aquí
                        subir_resultado_a_drive(nombre_archivo, contenido_json)
        else:
            with col2:
                st.info("No hay datos válidos para exportar.")


    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        if urls:
            with st.spinner(f"🔄 Scrapeando {len(urls)} hotel(es)... Esto puede tardar varios minutos."):
                # Si solo es una URL, podríamos usar el método síncrono simple para evitar complejidad de gather
                # if len(urls) == 1:
                #     resultado_sync, html_sync = obtener_datos_booking_sync(urls[0])
                #     st.session_state.resultados_json = [resultado_sync]
                #     if resultado_sync and not resultado_sync.get("error"):
                #        st.session_state.last_successful_html_content = html_sync
                # else:
                # Procesar en lote para múltiples URLs
                resultados_lote = asyncio.run(procesar_urls_en_lote(urls))
                st.session_state.resultados_json = resultados_lote
            st.rerun() # Reemplaza st.experimental_rerun()

    # Mostrar resultados y HTML
    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        # Mostrar todos los resultados, incluyendo los que tuvieron errores de scraping parcial
        st.json(st.session_state.resultados_json)

    if st.session_state.last_successful_html_content:
        st.subheader("📄 HTML capturado (del último scraping exitoso)")
        st.download_button(
            label="⬇️ Descargar HTML capturado",
            data=st.session_state.last_successful_html_content.encode("utf-8"),
            file_name=f"pagina_booking_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            key="descargar_html"
        )
