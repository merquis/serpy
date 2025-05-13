import streamlit as st
import asyncio
import json
import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
# import copy # No parece usarse explícitamente

# Importaciones locales (comentadas si no se usan aquí directamente)
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData (para Playwright)
# ════════════════════════════════════════════════════
def get_proxy_settings():
    """Lee la configuración del proxy desde st.secrets y la formatea para Playwright."""
    try:
        proxy_config = st.secrets["brightdata_booking"]
        host = proxy_config.get("host")
        port = proxy_config.get("port")
        username = proxy_config.get("username")
        password = proxy_config.get("password")
        if host and port and username and password:
            return {
                "server": f"http://{host}:{port}", 
                "username": username,
                "password": password
            }
        else: return None
    except KeyError: return None
    except Exception as e: print(f"Error inesperado leyendo config proxy: {e}"); return None

# ════════════════════════════════════════════════════
# 📅 Scraping Booking (Playwright - PRUEBA 3: Conteo y Bloqueo más Agresivo)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance):
    """PRUEBA 3: Obtiene datos, cuenta requests y aplica bloqueo más agresivo."""
    html = ""
    page = None
    resultado_final = {}
    
    # Usar listas para que puedan ser modificadas por la lambda/funciones internas
    request_counter_list = [0] 
    blocked_counter_list = [0]
    # allowed_urls_log = [] # Descomenta para depurar URLs permitidas

    try:
        page = await browser_instance.new_page(ignore_https_errors=True)
        
        def count_request_event_handler(request_obj):
            request_counter_list[0] += 1
            # print(f"Request #{request_counter_list[0]}: {request_obj.url}")

        page.on("request", count_request_event_handler)
        
        # --- OPTIMIZACIÓN: PRUEBA 3 - Bloqueo MÁS AGRESIVO ---
        print(f"Configurando bloqueo de recursos MÁS AGRESIVO para: {url}")

        DOMINIOS_GENERALES_A_BLOQUEAR = [
            "googletagmanager.com", "google-analytics.com", "analytics.google.com",
            "googletagservices.com", "tealiumiq.com", "tags.tiqcdn.com", 
            "adobedtm.com", "assets.adobedtm.com", "omtrdc.net", "dpm.demdex.net",
            "googlesyndication.com", "doubleclick.net", "adservice.google.com",
            "connect.facebook.net", "staticxx.facebook.com", "www.facebook.com/tr/",
            "criteo.com", "criteo.net", "static.criteo.net", "targeting.criteo.com",
            "adnxs.com", "optimizely.com", "scorecardresearch.com", "sb.scorecardresearch.com",
            "everesttech.net", "creativecdn.com", "yieldlab.net",
            "bing.com/ads", "bat.bing.com", "ads.microsoft.com",
            "cookielaw.org", "cdn.cookielaw.org", "onetrust.com", 
            "usercentrics.com", "app.usercentrics.eu",
            "krxd.net", "rlcdn.com", "casalemedia.com", "pubmatic.com", 
            "amazon-adsystem.com", "adsystem.amazon.com", "aax.amazon-adsystem.com",
            "nr-data.net", # New Relic
            # ¡AÑADE MÁS DOMINIOS DE TRACKING/ADS/ANALÍTICAS QUE IDENTIFIQUES!
        ]
        
        PATRONES_URL_A_BLOQUEAR_GENERAL = [
            "/tracking", "/analytics", "/ads", "/advert", "/banner",
            "beacon", "pixel", "collect", "gtm.js", "sdk.js",
            "optanon", "usercentrics", "challenge.js", "OtAutoBlock.js", "otSDKStub.js"
            # Añade patrones de scripts/xhr de cf.bstatic.com o booking.com que sepas que no son vitales
        ]
        
        # Dominios XHR/Fetch de terceros que podríamos bloquear (esta lista puede ser igual o un subconjunto)
        DOMINIOS_XHR_FETCH_A_BLOQUEAR = DOMINIOS_GENERALES_A_BLOQUEAR 

        def should_block_resource_aggressively(request_obj):
            res_type = request_obj.resource_type
            res_url = request_obj.url.lower()

            if res_type in ["image", "font", "media", "stylesheet"]:
                blocked_counter_list[0] += 1
                return True

            if res_type in ["script", "xhr", "fetch"]:
                # Excepción para no bloquear el documento HTML principal de la URL visitada
                if res_type == "document" and (url.lower() == res_url or request_obj.is_navigation_request()):
                    # nonlocal allowed_urls_log; allowed_urls_log.append(f"PERMITIDO (Navegación principal): {res_url}")
                    return False

                if "booking.com" in res_url or "bstatic.com" in res_url: 
                    for pattern in PATRONES_URL_A_BLOQUEAR_GENERAL:
                        if pattern in res_url:
                            blocked_counter_list[0] += 1
                            # print(f"BLOQ (patrón en booking/bstatic {res_type}): {res_url}")
                            return True
                    # nonlocal allowed_urls_log; allowed_urls_log.append(f"PERMITIDO (booking/bstatic {res_type}): {res_url}")
                    return False 

                for domain in DOMINIOS_GENERALES_A_BLOQUEAR:
                    if domain in res_url:
                        blocked_counter_list[0] += 1
                        return True
                for pattern in PATRONES_URL_A_BLOQUEAR_GENERAL:
                    if pattern in res_url:
                        blocked_counter_list[0] += 1
                        return True
            
            # nonlocal allowed_urls_log; allowed_urls_log.append(f"PERMITIDO (default {res_type}): {res_url}")
            return False

        await page.route("**/*", lambda route: route.abort() if should_block_resource_aggressively(route.request) else route.continue_())
        print("Bloqueo AGRESIVO configurado.")
        # --- Fin Optimización ---

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8" })
        
        print(f"Navegando a: {url}")
        await page.goto(url, timeout=100000, wait_until="domcontentloaded")
        
        try:
            selector_estable = "#hp_hotel_name" 
            print(f"Esperando selector estable: '{selector_estable}' para {url}")
            await page.wait_for_selector(selector_estable, state="visible", timeout=35000)
            print(f"Selector estable encontrado para {url}.")
        except PlaywrightTimeoutError:
            print(f"Advertencia: Selector estable '{selector_estable}' no encontrado en 35s para {url}. El HTML podría ser incompleto.")
        
        print(f"Intentando obtener page.content() para {url}...")
        html = await page.content()
        
        request_count = request_counter_list[0]
        blocked_request_count = blocked_counter_list[0]

        # print(f"--- URLs Permitidas para {url} ({request_count - blocked_request_count}) ---")
        # for allowed_url_item in allowed_urls_log:
        #     print(allowed_url_item)
        # print(f"--- Fin URLs Permitidas ---")
        
        print(f"HTML obtenido para {url} (Tamaño: {len(html)} bytes). Requests totales iniciados: {request_count}, Bloqueados: {blocked_request_count}")
        
        if not html:
            print(f"Error: HTML vacío para {url}.")
            return {"error": "Fallo_HTML_Vacio_Playwright", "url_original": url, "details": "No se obtuvo contenido HTML.", "request_count_total_iniciados": request_count, "request_count_bloqueados": blocked_request_count, "request_count_netos_estimados": request_count - blocked_request_count}, ""
        
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url)
        if isinstance(resultado_final, dict):
            resultado_final["request_count_total_iniciados"] = request_count
            resultado_final["request_count_bloqueados"] = blocked_request_count
            resultado_final["request_count_netos_estimados"] = request_count - blocked_request_count
        
    except PlaywrightTimeoutError as e:
        details = str(e); print(f"Timeout de Playwright para {url}: {details}")
        error_key = "Fallo_Timeout_PageGoto_Playwright" if "page.goto" in details.lower() else "Fallo_Timeout_Playwright"
        return {"error": error_key, "url_original": url, "details": details, "request_count_total_iniciados": request_count_counter_list[0], "request_count_bloqueados": blocked_counter_list[0], "request_count_netos_estimados": request_counter_list[0] - blocked_counter_list[0]}, ""
    except Exception as e:
        error_type = type(e).__name__; details = str(e)
        print(f"Error ({error_type}) procesando {url} con Playwright: {details}")
        error_key = "Fallo_PageContent_Inestable_Playwright" if "page is navigating" in details else f"Fallo_Excepcion_Playwright_{error_type}"
        return {"error": error_key, "url_original": url, "details": details, "request_count_total_iniciados": request_counter_list[0], "request_count_bloqueados": blocked_counter_list[0], "request_count_netos_estimados": request_counter_list[0] - blocked_counter_list[0]}, ""
    finally:
        if page:
            try: await page.close()
            except Exception as e: print(f"Error menor al cerrar página {url}: {e}")
    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (se mantiene igual)
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    """Parsea el HTML (BeautifulSoup) y extrae datos del hotel."""
    parsed_url = urlparse(url); query_params = parse_qs(parsed_url.query)
    group_adults = query_params.get('group_adults', [''])[0]
    group_children = query_params.get('group_children', [''])[0]
    no_rooms = query_params.get('no_rooms', [''])[0]
    checkin_year_month_day = query_params.get('checkin', [''])[0]
    checkout_year_month_day = query_params.get('checkout', [''])[0]
    dest_type = query_params.get('dest_type', [''])[0]
    data_extraida, imagenes_secundarias, servicios = {}, [], []
    
    try: # JSON-LD
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string); potential_hotels = []
                    if isinstance(data_json, list): potential_hotels.extend(data_json)
                    elif isinstance(data_json, dict): potential_hotels.append(data_json)
                    for item in potential_hotels:
                        if isinstance(item, dict) and item.get("@type") == "Hotel": data_extraida = item; break
                    if data_extraida: print(f"JSON-LD encontrado para {url}"); break
                except: continue
        if not data_extraida: print(f"Advertencia: No se encontró JSON-LD para Hotel en {url}")
    except Exception as e: print(f"Error extrayendo JSON-LD: {e}")
    
    try: # Imágenes
        scripts_json = soup.find_all('script', type='application/json')
        found_urls_img = set()
        for script in scripts_json:
            if script.string and ('large_url' in script.string or '"url_max300"' in script.string):
                try:
                    data_json = json.loads(script.string); stack = [data_json]
                    while stack and len(imagenes_secundarias) < 15:
                        current = stack.pop()
                        if isinstance(current, dict):
                            for k, v in current.items():
                                if k in ('large_url','url_max1280','url_original') and isinstance(v,str) and v.startswith('https://') and '.staticflickr.com' not in v:
                                    if v not in found_urls_img: imagenes_secundarias.append(v); found_urls_img.add(v)
                                elif isinstance(v, (dict, list)): stack.append(v)
                        elif isinstance(current, list): stack.extend(reversed(current))
                except: continue
        for img_tag in soup.find_all("img"): 
            src = img_tag.get("src")
            if src and src.startswith("https://cf.bstatic.com") and src not in found_urls_img and len(imagenes_secundarias) < 15 :
                 imagenes_secundarias.append(src); found_urls_img.add(src)
        if imagenes_secundarias: print(f"Se encontraron {len(imagenes_secundarias)} URLs de imágenes para {url}")
    except Exception as e: print(f"Error extrayendo imágenes: {e}")

    try: # Servicios
        possible_classes = ["hotel-facilities__list", "facilitiesChecklistSection", "hp_desc_important_facilities", "bui-list__description", "db29ecfbe2"]
        servicios_set = set()
        for cn in possible_classes:
             for container in soup.find_all(class_=cn):
                  for item in container.find_all(['li','span','div'], recursive=True):
                       texto = item.get_text(strip=True)
                       if texto and len(texto)>3 and 'icono' not in texto.lower() and 'mostrar' not in texto.lower(): servicios_set.add(texto)
        servicios = sorted(list(servicios_set))
        if servicios: print(f"Se encontraron {len(servicios)} servicios para {url}")
    except Exception as e: print(f"Error extrayendo servicios: {e}")

    titulo_h1_tag = soup.find("h1")
    titulo_h1 = titulo_h1_tag.get_text(strip=True) if titulo_h1_tag else data_extraida.get("name", "")
    if titulo_h1: print(f"Título H1 para {url}: {titulo_h1[:50]}...")
    else: print(f"Advertencia: No se encontró H1 para {url}")
    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
    if h2s: print(f"Se encontraron {len(h2s)} H2s para {url}")
    address_info = data_extraida.get("address", {}); rating_info = data_extraida.get("aggregateRating", {})
    return {
        "url_original": url, "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "metodo_extraccion": "Playwright_Prueba3",
        "busqueda_checkin": checkin_year_month_day, "busqueda_checkout": checkout_year_month_day,
        "busqueda_adultos": group_adults, "busqueda_ninos": group_children,
        "busqueda_habitaciones": no_rooms, "busqueda_tipo_destino": dest_type,
        "nombre_alojamiento": data_extraida.get("name", titulo_h1), "tipo_alojamiento": data_extraida.get("@type", "Desconocido"),
        "direccion": address_info.get("streetAddress"), "codigo_postal": address_info.get("postalCode"),
        "ciudad": address_info.get("addressLocality"), "pais": address_info.get("addressCountry"),
        "latitud": data_extraida.get("geo", {}).get("latitude"), "longitud": data_extraida.get("geo", {}).get("longitude"),
        "url_hotel_booking": data_extraida.get("url"), "descripcion_corta": data_extraida.get("description"),
        "valoracion_global": rating_info.get("ratingValue"), "mejor_valoracion_posible": rating_info.get("bestRating", "10"),
        "numero_opiniones": rating_info.get("reviewCount"), "rango_precios": data_extraida.get("priceRange"),
        "titulo_h1": titulo_h1, "subtitulos_h2": h2s, "servicios_principales": servicios, "imagenes": imagenes_secundarias,
    }

# ════════════════════════════════════════════════════
# 🗂️ Procesar Lote con Playwright (con opción de proxy)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar, use_proxy: bool):
    """Procesa URLs con Playwright, lanzando navegador CON o SIN proxy según se indique."""
    tasks_results = []
    proxy_conf_playwright = None
    browser_launch_options = {"headless": True} 
    if use_proxy:
        proxy_conf_playwright = get_proxy_settings()
        if not proxy_conf_playwright:
            print("Error: Se requiere proxy pero no está configurado en st.secrets.")
            return [{"error": "Proxy requerido pero no configurado", "url_original": url, "details": ""} for url in urls_a_procesar]
        else:
            browser_launch_options["proxy"] = proxy_conf_playwright
            print(f"Configurando lote Playwright para usar proxy: {proxy_conf_playwright['server']}")
    else:
        print("Configurando lote Playwright para ejecutarse SIN proxy.")
    async with async_playwright() as p:
        browser = None
        try:
            print(f"Lanzando navegador Playwright {'CON' if use_proxy and proxy_conf_playwright else 'SIN'} proxy...")
            browser = await p.chromium.launch(**browser_launch_options)
            print("Navegador Playwright lanzado.")
            tasks = [obtener_datos_booking_playwright(url, browser) for url in urls_a_procesar]
            results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
            temp_results = []
            for i, res_or_exc in enumerate(results_with_exceptions):
                url_p = urls_a_procesar[i]
                if isinstance(res_or_exc, Exception):
                    print(f"Excepción en gather (Playwright) para {url_p}: {res_or_exc}")
                    temp_results.append({"error": "Fallo_Excepcion_Gather_Playwright", "url_original": url_p, "details": str(res_or_exc)})
                elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                    res_dict, html_content = res_or_exc
                    if isinstance(res_dict, dict):
                        temp_results.append(res_dict)
                        if not res_dict.get("error") and html_content:
                            st.session_state.last_successful_html_content = html_content
                    else:
                        temp_results.append({"error": "Fallo_TipoResultadoInesperado_Playwright", "url_original": url_p, "details": f"Tipo: {type(res_dict)}"})
                else:
                    temp_results.append({"error": "Fallo_ResultadoInesperado_Playwright", "url_original": url_p, "details": str(res_or_exc)})
            tasks_results = temp_results
        except Exception as batch_error:
            print(f"Error crítico durante el procesamiento del lote (Playwright): {batch_error}")
            tasks_results = [{"error": "Fallo_Critico_Lote_Playwright", "url_original": url, "details": str(batch_error)} for url in urls_a_procesar]
        finally:
            if browser: await browser.close(); print("Navegador Playwright compartido cerrado.")
    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (con checkbox para proxy y usando Playwright)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renderiza la interfaz con opción de forzar proxy, usando Playwright."""
    st.session_state.setdefault("_called_script", "scraping_booking_playwright_prueba3")
    st.title("🏨 Scraping Hoteles Booking (Playwright Prueba 3)")
    
    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales", [])
    st.session_state.setdefault("last_successful_html_content", "")
    st.session_state.setdefault("force_proxy_checkbox", False)

    proxy_settings = get_proxy_settings(); proxy_ok = proxy_settings is not None
    if not proxy_ok:
        st.warning("⚠️ Proxy no configurado en st.secrets. El modo 'forzar proxy' y los reintentos con proxy no funcionarán como se espera.")

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150,
        placeholder="Ej: https://www.booking.com/hotel/es/nombre-hotel.es.html"
    )
    st.session_state.force_proxy_checkbox = st.checkbox(
        "Usar proxy directamente para todos los intentos (con Playwright)",
        value=st.session_state.force_proxy_checkbox, disabled=(not proxy_ok),
        help="Si se marca, todas las URLs se procesarán con Playwright y proxy (con bloqueo de recursos). Si no, se intentará con Playwright sin proxy, y se reintentarán los fallos con Playwright y proxy (ambos con bloqueo)."
    )
    optim_comment = "(Optimización Playwright: Bloqueo Agresivo de Scripts de Terceros y otros ACTIVO)"
    st.caption(optim_comment)

    col1, col2 = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear con Playwright", use_container_width=True)

    if buscar_btn:
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.strip() and "booking.com/hotel" in url.strip()]
        if not urls: st.warning("Introduce URLs válidas de Booking.com."); st.stop()

        forzar_proxy_directo = st.session_state.force_proxy_checkbox
        resultados_actuales = []
        st.session_state.last_successful_html_content = "" 

        if forzar_proxy_directo:
            if not proxy_ok:
                st.error("Error: Proxy directo seleccionado pero no configurado."); st.stop()
            with st.spinner(f"Procesando {len(urls)} URLs directamente CON proxy (Playwright y bloqueo agresivo)..."):
                resultados_actuales = asyncio.run(procesar_urls_en_lote(urls, use_proxy=True))
        else: 
            final_results_map = {}
            st.info("Nota: El bloqueo de recursos definido en el código se aplicará en AMBAS pasadas (con y sin proxy).")
            with st.spinner(f"Paso 1/2: Intentando {len(urls)} URLs SIN proxy (Playwright con bloqueo agresivo)..."):
                results_pass_1 = asyncio.run(procesar_urls_en_lote(urls, use_proxy=False))

            urls_a_reintentar = []
            for i, result in enumerate(results_pass_1):
                url_procesada_p1 = urls[i] 
                final_results_map[url_procesada_p1] = result
                if isinstance(result, dict) and result.get("error"):
                    urls_a_reintentar.append(url_procesada_p1)
                elif not isinstance(result, dict): 
                    urls_a_reintentar.append(url_procesada_p1)
                    final_results_map[url_procesada_p1] = {"error":"Fallo_FormatoInvalidoP1_Playwright", "url_original":url_procesada_p1, "details":"Resultado no fue diccionario ni excepción manejada"}

            if urls_a_reintentar:
                st.info(f"{len(urls_a_reintentar)} URL(s) fallaron sin proxy. Preparando reintento CON proxy (Playwright con bloqueo agresivo)...")
                if not proxy_ok:
                    st.error("Proxy no configurado. No se pueden reintentar las URLs fallidas con proxy.")
                else:
                    with st.spinner(f"Paso 2/2: Reintentando {len(urls_a_reintentar)} URL(s) CON proxy (Playwright con bloqueo agresivo)..."):
                        results_pass_2 = asyncio.run(procesar_urls_en_lote(urls_a_reintentar, use_proxy=True))
                    for i, result_retry in enumerate(results_pass_2):
                        url_retry = urls_a_reintentar[i]
                        if isinstance(result_retry, dict):
                            result_retry["nota"] = "Resultado tras reintento con proxy (Playwright)"
                            final_results_map[url_retry] = result_retry
                        else: 
                            final_results_map[url_retry] = {"error":"Fallo_FormatoInvalidoP2_Playwright", "url_original":url_retry, "details":"Resultado reintento no fue diccionario ni excepción manejada"}
            elif not forzar_proxy_directo :
                st.success("¡Todas las URLs se procesaron con éxito sin necesidad de proxy (usando Playwright con bloqueo agresivo)!")
            
            resultados_actuales = [final_results_map[url] for url in urls]

        st.session_state.resultados_finales = resultados_actuales
        st.rerun()

    if st.session_state.resultados_finales:
        st.markdown("---"); st.subheader("📊 Resultados Finales (Playwright)")
        num_exitos = sum(1 for r in st.session_state.resultados_finales if isinstance(r, dict) and not r.get("error"))
        num_fallos = len(st.session_state.resultados_finales) - num_exitos
        
        first_successful_result_requests = "N/A"
        first_successful_result_blocked = "N/A"
        first_successful_result_net = "N/A"
        for r_idx, r_val in enumerate(st.session_state.resultados_finales): # Renombrar para evitar conflicto
            if isinstance(r_val, dict) and not r_val.get("error") and "request_count_total_iniciados" in r_val:
                first_successful_result_requests = r_val["request_count_total_iniciados"]
                first_successful_result_blocked = r_val.get("request_count_bloqueados", "N/A")
                first_successful_result_net = r_val.get("request_count_netos_estimados", "N/A")
                break
        st.write(f"Procesados: {len(st.session_state.resultados_finales)} | Éxitos: {num_exitos} | Fallos: {num_fallos}")
        st.caption(f"Requests (aprox) en el primer éxito: {first_successful_result_net} (Iniciados: {first_successful_result_requests}, Bloqueados: {first_successful_result_blocked})")

        with st.expander("Ver resultados detallados (JSON)", expanded=(num_fallos > 0)):
             st.json(st.session_state.resultados_finales)

    if st.session_state.last_successful_html_content:
        st.markdown("---"); st.subheader("📄 Último HTML Capturado con Éxito")
        try:
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(label="⬇️ Descargar HTML", data=html_bytes,
                file_name="ultimo_hotel_booking_playwright.html", mime="text/html")
        except Exception as e: st.error(f"No se pudo preparar el HTML para descarga: {e}")

# --- Ejecutar ---
if __name__ == "__main__":
    render_scraping_booking()
