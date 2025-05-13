import streamlit as st
import asyncio
import json
import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# --------------------------------------------------------------------------
# Constantes de Configuración de Bloqueo (Personalizar según análisis)
# --------------------------------------------------------------------------
# Dominios de terceros a bloquear agresivamente (scripts, xhr, fetch)
DOMINIOS_TERCEROS_A_BLOQUEAR_AGRESIVO = [
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
    "usercentrics.com", "app.usercentrics.eu", "krxd.net", "rlcdn.com", 
    "casalemedia.com", "pubmatic.com", "amazon-adsystem.com", 
    "adsystem.amazon.com", "aax.amazon-adsystem.com", "nr-data.net",
    "edge.sdk.awswaf.com", # AWS WAF - probar si se puede bloquear
    # ¡AÑADE MÁS DOMINIOS DE TRACKING/ADS/ANALÍTICAS QUE IDENTIFIQUES!
]

# Patrones de URL para bloquear (se aplica a scripts/xhr/fetch de terceros Y booking/bstatic)
PATRONES_URL_A_BLOQUEAR_AGRESIVO = [
    "/tracking", "/analytics", "/ads", "/advert", "/banner",
    "beacon", "pixel", "collect", "gtm.js", "sdk.js",
    "optanon", "usercentrics", "challenge.js", "OtAutoBlock.js", "otSDKStub.js",
    # Añade patrones de cf.bstatic.com o booking.com que sepas que no son vitales
    # Ejemplo (ARRIESGADO): "cf.bstatic.com/static/js/experiments/" 
]

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData
# ════════════════════════════════════════════════════
def get_proxy_settings():
    """Lee la configuración del proxy desde st.secrets y la formatea para Playwright."""
    try:
        proxy_config_secrets = st.secrets["brightdata_booking"]
        host = proxy_config_secrets.get("host")
        port = proxy_config_secrets.get("port")
        username = proxy_config_secrets.get("username")
        password = proxy_config_secrets.get("password")
        if host and port and username and password:
            return {"server": f"http://{host}:{port}", "username": username, "password": password}
        else: print("Advertencia: Faltan datos de proxy en st.secrets."); return None
    except KeyError: print("Advertencia: Sección [brightdata_booking] no encontrada en st.secrets."); return None
    except Exception as e: print(f"Error leyendo config proxy: {e}"); return None

# ════════════════════════════════════════════════════
# 헬 Función de Decisión de Bloqueo de Recursos
# ════════════════════════════════════════════════════
def should_block_resource(request_obj, current_page_url: str, is_aggressive_mode: bool, blocked_counter_list: list):
    """Decide si un recurso debe ser bloqueado."""
    res_type = request_obj.resource_type
    res_url = request_obj.url.lower()

    # Bloqueo Ligero (cuando is_aggressive_mode es False - intento sin proxy)
    if not is_aggressive_mode:
        if res_type in ["image", "font", "media"]: # Solo bloquear estos básicos
            blocked_counter_list[0] += 1
            return True
        return False # Permitir CSS, todos los scripts, xhr, fetch

    # Bloqueo Agresivo (cuando is_aggressive_mode es True - intento con proxy)
    if res_type in ["image", "font", "media", "stylesheet"]:
        blocked_counter_list[0] += 1
        return True

    if res_type in ["script", "xhr", "fetch"]:
        # No bloquear el documento HTML principal de la URL que estamos visitando
        if res_type == "document" and (current_page_url.lower() == res_url or request_obj.is_navigation_request()):
            return False

        # Para booking.com y bstatic.com, solo bloquear por patrones específicos
        if "booking.com" in res_url or "bstatic.com" in res_url: 
            for pattern in PATRONES_URL_A_BLOQUEAR_AGRESIVO: # Patrones para booking/bstatic
                if pattern in res_url:
                    # print(f"BLOQ (AGRESIVO - patrón booking/bstatic {res_type}): {res_url}")
                    blocked_counter_list[0] += 1
                    return True
            return False # Permitir si no coincide con un patrón de bloqueo agresivo
        
        # Para otros dominios (terceros), aplicar bloqueo general agresivo
        for domain in DOMINIOS_TERCEROS_A_BLOQUEAR_AGRESIVO:
            if domain in res_url:
                # print(f"BLOQ (AGRESIVO - dominio tercero {res_type}): {res_url}")
                blocked_counter_list[0] += 1
                return True
        for pattern in PATRONES_URL_A_BLOQUEAR_AGRESIVO: 
            if pattern in res_url:
                # print(f"BLOQ (AGRESIVO - patrón tercero {res_type}): {res_url}")
                blocked_counter_list[0] += 1
                return True
                
    return False # Permitir por defecto en modo agresivo si no se especifica lo contrario

# ════════════════════════════════════════════════════
# 📅 Scraping Booking con Playwright (Bloqueo Condicional)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance, use_aggressive_blocking: bool):
    html = ""
    page = None
    resultado_final = {}
    request_counter_list = [0] 
    blocked_counter_list = [0]

    try:
        page = await browser_instance.new_page(ignore_https_errors=True)
        
        page.on("request", lambda req: request_counter_list[0] +_ 1) # Corregido el incremento aquí
        
        print(f"Configurando bloqueo (Agresivo: {use_aggressive_blocking}) para: {url}")
        await page.route("**/*", lambda route: route.abort() if should_block_resource(route.request, url, use_aggressive_blocking, blocked_counter_list) else route.continue_())
        
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8" })
        
        print(f"Navegando a: {url} (Bloqueo agresivo: {use_aggressive_blocking})")
        # Si el bloqueo es ligero (sin proxy), domcontentloaded es más seguro.
        # Si el bloqueo es agresivo (con proxy), 'load' podría ser más robusto si JS es complejo.
        wait_until_event = "load" if use_aggressive_blocking else "domcontentloaded"
        await page.goto(url, timeout=120000, wait_until=wait_until_event) 
        
        try:
            selector_estable = "#hp_hotel_name" 
            await page.wait_for_selector(selector_estable, state="visible", timeout=40000)
        except PlaywrightTimeoutError:
            print(f"Advertencia: Selector estable '{selector_estable}' no encontrado en 40s para {url}.")
        
        if use_aggressive_blocking: 
            await page.wait_for_timeout(2000) 

        html = await page.content()
        
        request_count = request_counter_list[0]
        blocked_request_count = blocked_counter_list[0] 
        net_requests = request_count - blocked_request_count
        
        print(f"HTML para {url} (Tamaño: {len(html)}B). Iniciados: {request_count}, Bloqueados: {blocked_request_count}, Netos: {net_requests}")
        
        if not use_aggressive_blocking and "<noscript>" in html.lower() and "javascript is disabled" in html.lower():
            print(f"Página 'JavaScript Deshabilitado' detectada para {url} (intento sin proxy).")
            return {"error": "Fallo_JavaScript_Deshabilitado", "url_original": url, "details": "Booking.com requiere JavaScript o el bloqueo ligero no fue suficiente.", "request_count_total_iniciados": request_count, "request_count_bloqueados": blocked_request_count, "request_count_netos_estimados": net_requests}, ""
        
        if not html:
            print(f"Error: HTML vacío para {url}.")
            return {"error": "Fallo_HTML_Vacio_Playwright", "url_original": url, "details": "No se obtuvo contenido HTML.", "request_count_total_iniciados": request_count, "request_count_bloqueados": blocked_request_count, "request_count_netos_estimados": net_requests}, ""
        
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url)
        if isinstance(resultado_final, dict):
            resultado_final["request_count_total_iniciados"] = request_count
            resultado_final["request_count_bloqueados"] = blocked_request_count
            resultado_final["request_count_netos_estimados"] = net_requests
        
    except PlaywrightTimeoutError as e:
        details = str(e); print(f"Timeout de Playwright para {url}: {details}")
        error_key = "Fallo_Timeout_PageGoto_Playwright" if "page.goto" in details.lower() else "Fallo_Timeout_Playwright"
        return {"error": error_key, "url_original": url, "details": details, "request_count_total_iniciados": request_counter_list[0], "request_count_bloqueados": blocked_counter_list[0], "request_count_netos_estimados": request_counter_list[0] - blocked_counter_list[0]}, ""
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
# 📋 Parsear HTML de Booking
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    parsed_url = urlparse(url); query_params = parse_qs(parsed_url.query)
    group_adults = query_params.get('group_adults', [''])[0]
    group_children = query_params.get('group_children', [''])[0]
    no_rooms = query_params.get('no_rooms', [''])[0]
    checkin_year_month_day = query_params.get('checkin', [''])[0]
    checkout_year_month_day = query_params.get('checkout', [''])[0]
    dest_type = query_params.get('dest_type', [''])[0]
    data_extraida, imagenes_secundarias, servicios = {}, [], []
    
    try: 
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string); potential_hotels = []
                    if isinstance(data_json, list): potential_hotels.extend(data_json)
                    elif isinstance(data_json, dict): potential_hotels.append(data_json)
                    for item in potential_hotels:
                        if isinstance(item, dict) and item.get("@type") == "Hotel": 
                            data_extraida = item; break
                    if data_extraida: break 
                except json.JSONDecodeError as je: 
                    print(f"Advertencia: Script JSON-LD no pudo ser decodificado en {url}: {je}")
                    continue
    except Exception as e: print(f"Error general extrayendo JSON-LD para {url}: {e}")
    
    try: 
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
                                    if v not in found_urls_img: 
                                        imagenes_secundarias.append(v); found_urls_img.add(v)
                                elif isinstance(v, (dict, list)): stack.append(v)
                        elif isinstance(current, list): stack.extend(reversed(current))
                except json.JSONDecodeError as je:
                    print(f"Advertencia: Script JSON de imágenes no pudo ser decodificado en {url}: {je}")
                    continue
        for img_tag in soup.find_all("img"): 
            src = img_tag.get("src")
            if src and src.startswith("https://cf.bstatic.com") and src not in found_urls_img and len(imagenes_secundarias) < 15 :
                 imagenes_secundarias.append(src); found_urls_img.add(src)
    except Exception as e: print(f"Error general extrayendo imágenes para {url}: {e}")

    try: 
        possible_classes = ["hotel-facilities__list", "facilitiesChecklistSection", "hp_desc_important_facilities", "bui-list__description", "db29ecfbe2"]
        servicios_set = set()
        for cn in possible_classes:
             for container in soup.find_all(class_=cn):
                  for item in container.find_all(['li','span','div'], recursive=True):
                       texto = item.get_text(strip=True)
                       if texto and len(texto)>3 and 'icono' not in texto.lower() and 'mostrar' not in texto.lower(): 
                           servicios_set.add(texto)
        servicios = sorted(list(servicios_set))
    except Exception as e: print(f"Error general extrayendo servicios para {url}: {e}")

    titulo_h1_tag = soup.find("h1")
    titulo_h1 = titulo_h1_tag.get_text(strip=True) if titulo_h1_tag else data_extraida.get("name", "")
    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
    address_info = data_extraida.get("address", {}); rating_info = data_extraida.get("aggregateRating", {})
    
    return {
        "url_original": url, "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "metodo_extraccion": "Playwright_Optimizado_BloqueoCondicional", # Actualizado
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
# 🗂️ Procesar Lote con Playwright (adaptado para bloqueo condicional)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar, use_proxy: bool, use_aggressive_blocking: bool): # Parámetro añadido
    """Procesa URLs con Playwright, con bloqueo de recursos condicional."""
    tasks_results = []
    proxy_conf_playwright = None
    browser_launch_options = {"headless": True} 

    if use_proxy:
        proxy_conf_playwright = get_proxy_settings()
        if not proxy_conf_playwright:
            print("Error: Proxy requerido pero no configurado.")
            return [{"error": "Proxy requerido pero no configurado", "url_original": url, "details": ""} for url in urls_a_procesar]
        else:
            browser_launch_options["proxy"] = proxy_conf_playwright
            print(f"Lote Playwright: Usando proxy: {proxy_conf_playwright['server']}")
    else:
        print(f"Lote Playwright: Ejecutando SIN proxy (Bloqueo agresivo: {use_aggressive_blocking}).")
    
    async with async_playwright() as p:
        browser = None
        try:
            print(f"Lanzando navegador Playwright (Proxy: {use_proxy}, Bloqueo Agresivo: {use_aggressive_blocking})...")
            browser = await p.chromium.launch(**browser_launch_options)
            print("Navegador Playwright lanzado.")
            
            tasks = [obtener_datos_booking_playwright(url, browser, use_aggressive_blocking=use_aggressive_blocking) for url in urls_a_procesar]
            results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
            
            temp_results = []
            for i, res_or_exc in enumerate(results_with_exceptions):
                url_p = urls_a_procesar[i]
                if isinstance(res_or_exc, Exception):
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
            print(f"Error crítico lote (Playwright): {batch_error}")
            tasks_results = [{"error": "Fallo_Critico_Lote_Playwright", "url_original": "Lote Completo", "details": str(batch_error)}]
        finally:
            if browser: await browser.close(); print("Navegador Playwright compartido cerrado.")
    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (con lógica de 2 Pasadas y bloqueo condicional)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.session_state.setdefault("_called_script", "scraping_booking_playwright_refactor_final")
    st.title("🏨 Scraping Hoteles Booking (Playwright Optimizado vFinal)")
    
    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales", [])
    st.session_state.setdefault("last_successful_html_content", "")
    st.session_state.setdefault("force_proxy_checkbox", False)

    proxy_settings = get_proxy_settings(); proxy_ok = proxy_settings is not None
    if not proxy_ok:
        st.warning("⚠️ Proxy no configurado. El modo 'forzar proxy' y los reintentos con proxy no funcionarán.")

    st.session_state.urls_input = st.text_area(
        "📝 URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150,
        placeholder="Ej: https://www.booking.com/hotel/es/nombre-hotel.es.html"
    )
    st.session_state.force_proxy_checkbox = st.checkbox(
        "Usar proxy directamente (con bloqueo agresivo de recursos)",
        value=st.session_state.force_proxy_checkbox, disabled=(not proxy_ok),
        help="Si se marca, TODAS las URLs usan proxy + bloqueo agresivo. Si NO, se intenta SIN proxy + bloqueo LIGERO, y los fallos se reintentan CON proxy + bloqueo AGRESIVO."
    )
    st.caption("Bloqueo: Ligero (sin proxy, permite CSS/JS), Agresivo (con proxy, bloquea CSS y scripts de terceros).")

    col1, col2 = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear Hoteles", use_container_width=True)

    if buscar_btn:
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.strip() and "booking.com/hotel" in url.strip()] # Simple validación
        if not urls: st.warning("Introduce URLs válidas de Booking.com."); st.stop()

        forzar_proxy_directo = st.session_state.force_proxy_checkbox
        st.session_state.last_successful_html_content = "" 
        final_results_map = {url: None for url in urls} # Para mantener el orden y actualizar

        if forzar_proxy_directo:
            if not proxy_ok:
                st.error("Error: Proxy directo seleccionado pero no configurado."); st.stop()
            with st.spinner(f"Procesando {len(urls)} URLs CON proxy y bloqueo AGRESIVO..."):
                results_pass_direct_proxy = asyncio.run(procesar_urls_en_lote(urls, use_proxy=True, use_aggressive_blocking=True))
            for i, result in enumerate(results_pass_direct_proxy):
                final_results_map[urls[i]] = result
        else: 
            with st.spinner(f"Paso 1/2: Intentando {len(urls)} URLs SIN proxy (bloqueo LIGERO)..."):
                results_pass_1 = asyncio.run(procesar_urls_en_lote(urls, use_proxy=False, use_aggressive_blocking=False))

            urls_a_reintentar_map = {} # Guardar el resultado del primer intento para no perderlo
            for i, result in enumerate(results_pass_1):
                url_procesada_p1 = urls[i] 
                final_results_map[url_procesada_p1] = result # Guardar resultado P1 (sea éxito o fallo)
                if (isinstance(result, dict) and result.get("error")):
                    urls_a_reintentar_map[url_procesada_p1] = result # Marcar para reintento
                elif not isinstance(result, dict): 
                    urls_a_reintentar_map[url_procesada_p1] = {"error":"Fallo_FormatoInvalidoP1_Playwright", "url_original":url_procesada_p1, "details":"Resultado no fue diccionario"}
            
            urls_list_to_retry = list(urls_a_reintentar_map.keys())

            if urls_list_to_retry:
                if not proxy_ok:
                    st.error("Proxy no configurado. No se pueden reintentar las URLs fallidas con proxy. Mostrando resultados del primer intento.")
                else:
                    st.info(f"{len(urls_list_to_retry)} URL(s) necesitan reintento. Preparando CON proxy y bloqueo AGRESIVO...")
                    with st.spinner(f"Paso 2/2: Reintentando {len(urls_list_to_retry)} URL(s) CON proxy y bloqueo AGRESIVO..."):
                        results_pass_2 = asyncio.run(procesar_urls_en_lote(urls_list_to_retry, use_proxy=True, use_aggressive_blocking=True))
                    for i, result_retry in enumerate(results_pass_2):
                        url_retry = urls_list_to_retry[i]
                        if isinstance(result_retry, dict):
                            if not result_retry.get("error"): # Si el reintento fue exitoso
                                result_retry["nota"] = "Resultado tras reintento con proxy (bloqueo agresivo)"
                            else: # Si el reintento también falló
                                result_retry["nota"] = f"Fallo en reintento con proxy (bloqueo agresivo). Error original P1: {urls_a_reintentar_map[url_retry].get('error', 'N/A')}"
                            final_results_map[url_retry] = result_retry 
                        else:
                            final_results_map[url_retry] = {"error":"Fallo_FormatoInvalidoP2_Playwright", "url_original":url_retry, "details":"Resultado reintento no fue diccionario"}
            elif not forzar_proxy_directo : 
                st.success("¡Todas las URLs se procesaron con éxito sin necesidad de proxy (con bloqueo ligero)!")
        
        st.session_state.resultados_finales = [final_results_map[url] for url in urls] # Reconstruir en orden original
        st.rerun()

    if st.session_state.resultados_finales:
        st.markdown("---"); st.subheader("📊 Resultados Finales (Playwright)")
        resultados = st.session_state.resultados_finales
        num_exitos = sum(1 for r in resultados if isinstance(r, dict) and not r.get("error"))
        num_fallos = len(resultados) - num_exitos
        first_successful_result_requests = "N/A"; first_successful_result_blocked = "N/A"; first_successful_result_net = "N/A"
        for r_val in resultados:
            if isinstance(r_val, dict) and not r_val.get("error") and "request_count_total_iniciados" in r_val:
                first_successful_result_requests = r_val["request_count_total_iniciados"]
                first_successful_result_blocked = r_val.get("request_count_bloqueados", "N/A")
                first_successful_result_net = r_val.get("request_count_netos_estimados", "N/A")
                break
        st.write(f"Procesados: {len(resultados)} | Éxitos: {num_exitos} | Fallos: {num_fallos}")
        st.caption(f"Requests (aprox) en el primer éxito: {first_successful_result_net} (Iniciados: {first_successful_result_requests}, Bloqueados: {first_successful_result_blocked})")
        with st.expander("Ver resultados detallados (JSON)", expanded=(num_fallos > 0)):
             st.json(resultados)

    if st.session_state.last_successful_html_content:
        st.markdown("---"); st.subheader("📄 Último HTML Capturado con Éxito")
        try:
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(label="⬇️ Descargar HTML", data=html_bytes,
                file_name="ultimo_hotel_booking_playwright.html", mime="text/html")
        except Exception as e: st.error(f"No se pudo preparar el HTML para descarga: {e}")

if __name__ == "__main__":
    render_scraping_booking()
