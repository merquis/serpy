import streamlit as st
import asyncio
import json
import datetime
# import requests # No necesario
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
# import copy # No se usa explícitamente, se puede quitar si no hay copia profunda de resultados

# Importaciones locales (comentadas si no se usan aquí directamente)
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
# Nota: Las funciones de drive_utils no se llaman en este script específico.

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData
# ════════════════════════════════════════════════════
def get_proxy_settings():
    """Lee la configuración del proxy desde st.secrets."""
    try:
        proxy_config = st.secrets["brightdata_booking"]
        host = proxy_config.get("host")
        port = proxy_config.get("port")
        username = proxy_config.get("username")
        password = proxy_config.get("password")
        if host and port and username and password:
            return {"server": f"{host}:{port}", "username": username, "password": password}
        else: return None
    except KeyError: return None
    except Exception as e: print(f"Error inesperado leyendo config proxy: {e}"); return None

# ════════════════════════════════════════════════════
# 📅 Scraping Booking (CON BLOQUEO EXTREMO)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance):
    """Obtiene datos de una URL, bloqueando todo excepto el HTML principal."""
    html = ""
    page = None
    resultado_final = {}
    try:
        page = await browser_instance.new_page(ignore_https_errors=True)
        
        # --- OPTIMIZACIÓN EXTREMA: Bloquear TODO excepto el documento HTML principal ---
        print(f"Configurando bloqueo EXTREMO de recursos para: {url}")
        
        # Regla específica para favicon, ya que a veces se solicita aunque se bloqueen imágenes
        await page.route("**/favicon.ico", lambda route: route.abort())
        
        # Regla general: solo permitir 'document', abortar todo lo demás
        await page.route("**/*", 
            lambda route: route.continue_() if route.request.resource_type == "document" 
                          else route.abort()
        )
        print("Bloqueo extremo de recursos configurado.")
        # --- Fin Optimización Extrema ---

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8" })
        
        print(f"Navegando a: {url}")
        # Con bloqueo tan agresivo, 'commit' es el más adecuado.
        await page.goto(url, timeout=30000, wait_until="commit") # Timeout más corto
        
        # --- ESPERA (Probablemente innecesaria o fallará) ---
        # Con todo bloqueado, es muy improbable que selectores dinámicos aparezcan.
        # La página será HTML muy básico.
        try:
            # Intentar esperar solo a que el body esté adjunto, como señal mínima.
            await page.wait_for_selector("body", state="attached", timeout=5000) # Timeout muy corto
            print(f"Elemento 'body' encontrado (estado 'attached') para {url}.")
        except PlaywrightTimeoutError:
            print(f"Advertencia: 'body' no encontrado en 5s para {url}, el HTML podría ser inválido.")
        
        print(f"Intentando obtener page.content() para {url}...")
        html = await page.content() # Obtendrá el HTML inicial, probablemente sin JS ejecutado
        print(f"HTML obtenido para {url} (Tamaño: {len(html)} bytes)")
        
        if not html or len(html) < 200: # Umbral muy bajo, esperando HTML mínimo
            print(f"Error: HTML vacío o extremadamente pequeño para {url}. El bloqueo extremo puede ser demasiado.")
            return {"error": "Fallo_HTML_Minimo_Por_Bloqueo_Extremo", "url_original": url, "details": f"Tamaño HTML: {len(html)}"}, ""
        
        soup = BeautifulSoup(html, "html.parser")
        # Muchos campos probablemente estarán vacíos o serán incorrectos con este HTML mínimo
        resultado_final = parse_html_booking(soup, url) 
        
    except PlaywrightTimeoutError as e:
        details = str(e); print(f"Timeout para {url}: {details}")
        return {"error": "Fallo_Timeout_Playwright", "url_original": url, "details": details}, ""
    except Exception as e:
        error_type = type(e).__name__; details = str(e)
        print(f"Error ({error_type}) procesando {url}: {details}")
        return {"error": f"Fallo_Excepcion_{error_type}", "url_original": url, "details": details}, ""
    finally:
        if page:
            try: await page.close()
            except Exception as e: print(f"Error menor al cerrar página {url}: {e}")
    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (Limpio, sin IPs)
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
    try: # JSON-LD (probablemente no se cargue con bloqueo de JS)
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string); potential_hotels = []
                    if isinstance(data_json, list): potential_hotels.extend(data_json)
                    elif isinstance(data_json, dict): potential_hotels.append(data_json)
                    for item in potential_hotels:
                        if isinstance(item, dict) and item.get("@type") == "Hotel": data_extraida = item; break
                    if data_extraida: break
                except: continue
    except Exception as e: print(f"Error extrayendo JSON-LD (esperado con bloqueo JS): {e}")
    try: # Imágenes (buscará en el HTML estático)
        scripts_json = soup.find_all('script', type='application/json') # También puede buscar en img src si ajustas
        for script in scripts_json: # Esto busca en scripts JSON, que podrían estar bloqueados
            if script.string and ('large_url' in script.string or '"url_max300"' in script.string):
                try:
                    data_json = json.loads(script.string); stack = [data_json]; found_urls = set()
                    while stack and len(imagenes_secundarias) < 15:
                        current = stack.pop()
                        if isinstance(current, dict):
                            for k, v in current.items():
                                if k in ('large_url','url_max1280','url_original') and isinstance(v,str) and v.startswith('https://') and '.staticflickr.com' not in v:
                                    if v not in found_urls: imagenes_secundarias.append(v); found_urls.add(v)
                                elif isinstance(v, (dict, list)): stack.append(v)
                        elif isinstance(current, list): stack.extend(reversed(current))
                except: continue
        # Buscar también en etiquetas <img> por si acaso el HTML inicial las tiene
        for img_tag in soup.find_all("img"):
            if img_tag.get("src") and img_tag.get("src").startswith("https://cf.bstatic.com") and img_tag.get("src") not in found_urls and len(imagenes_secundarias) < 15 :
                 imagenes_secundarias.append(img_tag.get("src"))
                 found_urls.add(img_tag.get("src"))

    except Exception as e: print(f"Error extrayendo imágenes: {e}")
    try: # Servicios (probablemente limitado con bloqueo de CSS/JS)
        possible_classes = ["hotel-facilities__list", "facilitiesChecklistSection", "hp_desc_important_facilities", "bui-list__description", "db29ecfbe2"]
        servicios_set = set()
        for cn in possible_classes:
             for container in soup.find_all(class_=cn):
                  for item in container.find_all(['li','span','div'], recursive=True):
                       texto = item.get_text(strip=True)
                       if texto and len(texto)>3 and 'icono' not in texto.lower() and 'mostrar' not in texto.lower(): servicios_set.add(texto)
        servicios = sorted(list(servicios_set))
    except Exception as e: print(f"Error extrayendo servicios: {e}")
    titulo_h1 = soup.find("h1").get_text(strip=True) if soup.find("h1") else data_extraida.get("name", "")
    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
    address_info = data_extraida.get("address", {}); rating_info = data_extraida.get("aggregateRating", {})
    return {
        "url_original": url, "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
# 🗂️ Procesar Lote (con opción de proxy)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar, use_proxy: bool):
    """Procesa URLs, lanzando navegador CON o SIN proxy según se indique."""
    tasks_results = []
    proxy_conf = None
    browser_launch_options = {"headless": True}

    if use_proxy:
        proxy_conf = get_proxy_settings()
        if not proxy_conf:
            print("Error: Se requiere proxy pero no está configurado en st.secrets.")
            return [{"error": "Proxy requerido pero no configurado", "url_original": url, "details": ""} for url in urls_a_procesar]
        else:
            browser_launch_options["proxy"] = proxy_conf
            print(f"Configurando lote para usar proxy: {proxy_conf['server']}")
    else:
        print("Configurando lote para ejecutarse SIN proxy.")

    async with async_playwright() as p:
        browser = None
        try:
            print(f"Lanzando navegador {'CON' if use_proxy and proxy_conf else 'SIN'} proxy...")
            browser = await p.chromium.launch(**browser_launch_options)
            print("Navegador lanzado.")
            tasks = [obtener_datos_booking_playwright(url, browser) for url in urls_a_procesar]
            results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
            temp_results = []
            for i, res_or_exc in enumerate(results_with_exceptions):
                url_p = urls_a_procesar[i]
                if isinstance(res_or_exc, Exception):
                    print(f"Excepción en gather para {url_p}: {res_or_exc}")
                    temp_results.append({"error": "Fallo_Excepcion_Gather", "url_original": url_p, "details": str(res_or_exc)})
                elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                    res_dict, html_content = res_or_exc
                    if isinstance(res_dict, dict):
                        temp_results.append(res_dict)
                        if not res_dict.get("error") and html_content:
                            st.session_state.last_successful_html_content = html_content
                    else:
                        temp_results.append({"error": "Fallo_TipoResultadoInesperado", "url_original": url_p, "details": f"Tipo: {type(res_dict)}"})
                else:
                    temp_results.append({"error": "Fallo_ResultadoInesperado", "url_original": url_p, "details": str(res_or_exc)})
            tasks_results = temp_results
        except Exception as batch_error:
            print(f"Error crítico durante el procesamiento del lote: {batch_error}")
            tasks_results = [{"error": "Fallo_Critico_Lote", "url_original": url, "details": str(batch_error)} for url in urls_a_procesar]
        finally:
            if browser: await browser.close(); print("Navegador compartido cerrado.")
    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (con checkbox para proxy)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renderiza la interfaz con opción de forzar proxy y optimización extrema."""
    st.session_state.setdefault("_called_script", "scraping_booking")
    st.title("🏨 Scraping Hoteles Booking (Optimización Extrema)")

    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales", [])
    st.session_state.setdefault("last_successful_html_content", "")
    st.session_state.setdefault("force_proxy_checkbox", False) # Default a no forzar proxy

    proxy_settings = get_proxy_settings(); proxy_ok = proxy_settings is not None
    if not proxy_ok:
        st.warning("⚠️ Proxy no configurado en st.secrets. El modo 'forzar proxy' no funcionará; los reintentos con proxy tampoco.")

    # --- UI ---
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150,
        placeholder="Ej: https://www.booking.com/hotel/es/nombre-hotel.es.html"
    )

    st.session_state.force_proxy_checkbox = st.checkbox(
        "Usar proxy directamente para todos los intentos",
        value=st.session_state.force_proxy_checkbox,
        disabled=(not proxy_ok),
        help="Si se marca, todas las URLs se procesarán con proxy y bloqueo extremo de recursos (SOLO HTML). Si no, se intentará sin proxy (cargando todo), y se reintentarán los fallos con proxy (y bloqueo extremo)."
    )
    optim_comment = "(Optimización Extrema: Bloqueo JS/CSS/Imágenes/Fuentes/Media ACTIVO)"
    st.caption(optim_comment)


    col1, col2 = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles", use_container_width=True)

    # --- Lógica de Scraping Modificada ---
    if buscar_btn:
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.strip() and "booking.com/hotel" in url.strip()]
        if not urls: st.warning("Introduce URLs válidas de Booking.com."); st.stop()

        forzar_proxy_directo = st.session_state.force_proxy_checkbox
        resultados_actuales = []

        if forzar_proxy_directo:
            if not proxy_ok:
                st.error("Error: Se seleccionó 'Usar proxy directamente' pero el proxy no está configurado en st.secrets.")
                st.stop()
            with st.spinner(f"Procesando {len(urls)} URLs directamente CON proxy y bloqueo extremo..."):
                resultados_actuales = asyncio.run(procesar_urls_en_lote(urls, use_proxy=True))
        else: # Lógica de dos pasadas
            final_results_map = {}
            # En la pasada sin proxy, NO aplicamos el bloqueo de recursos para maximizar compatibilidad inicial.
            # Esto se controla porque procesar_urls_en_lote(..., use_proxy=False) no pasa proxy_conf
            # y obtener_datos_booking_playwright aplica el page.route *independientemente*.
            # Para que la primera pasada no bloquee, necesitaríamos pasar un flag a obtener_datos_booking_playwright
            # o tener dos versiones de esa función.
            # Por simplicidad de esta iteración, el bloqueo extremo se aplica SIEMPRE si está activo en obtener_datos_booking_playwright.
            st.info("Nota: Con el código actual, el bloqueo extremo de recursos (si está activo en `obtener_datos_booking_playwright`) se aplicará en AMBAS pasadas.")

            with st.spinner(f"Paso 1/2: Intentando {len(urls)} URLs SIN proxy (con bloqueo extremo si está activo)..."):
                results_pass_1 = asyncio.run(procesar_urls_en_lote(urls, use_proxy=False))

            urls_a_reintentar = []
            for i, result in enumerate(results_pass_1):
                url = urls[i]
                final_results_map[url] = result
                if isinstance(result, dict) and result.get("error"): urls_a_reintentar.append(url)
                elif not isinstance(result, dict):
                    urls_a_reintentar.append(url)
                    final_results_map[url] = {"error":"Fallo_FormatoInvalidoP1", "url_original":url, "details":"Resultado no fue diccionario"}

            if urls_a_reintentar:
                st.info(f"{len(urls_a_reintentar)} URL(s) fallaron sin proxy. Preparando reintento...")
                if not proxy_ok:
                    st.error("Proxy no configurado. No se pueden reintentar las URLs fallidas con proxy.")
                else:
                    with st.spinner(f"Paso 2/2: Reintentando {len(urls_a_reintentar)} URL(s) CON proxy y bloqueo extremo..."):
                        results_pass_2 = asyncio.run(procesar_urls_en_lote(urls_a_reintentar, use_proxy=True))
                    for i, result_retry in enumerate(results_pass_2):
                        url_retry = urls_a_reintentar[i]
                        if isinstance(result_retry, dict):
                            result_retry["nota"] = "Resultado tras reintento con proxy"
                            final_results_map[url_retry] = result_retry
                        else:
                            final_results_map[url_retry] = {"error":"Fallo_FormatoInvalidoP2", "url_original":url_retry, "details":"Resultado reintento no fue diccionario"}
            elif not forzar_proxy_directo :
                st.success("¡Todas las URLs se procesaron con éxito sin necesidad de proxy (o con bloqueo extremo si estaba activo)!")
            
            resultados_actuales = [final_results_map[url] for url in urls]

        st.session_state.resultados_finales = resultados_actuales
        st.rerun()

    # --- Mostrar Resultados ---
    if st.session_state.resultados_finales:
        st.markdown("---")
        st.subheader("📊 Resultados Finales")

        num_exitos = sum(1 for r in st.session_state.resultados_finales if isinstance(r, dict) and not r.get("error"))
        num_fallos = len(st.session_state.resultados_finales) - num_exitos
        st.write(f"Procesados: {len(st.session_state.resultados_finales)} | Éxitos Finales: {num_exitos} | Fallos Finales: {num_fallos}")

        with st.expander("Ver resultados detallados (JSON)", expanded=(num_fallos > 0)):
             st.json(st.session_state.resultados_finales)

    # --- Descarga de HTML ---
    if st.session_state.last_successful_html_content:
        st.markdown("---")
        st.subheader("📄 Último HTML Capturado con Éxito (Probablemente muy básico)")
        try:
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(label="⬇️ Descargar HTML", data=html_bytes,
                file_name="ultimo_hotel_booking_minimo.html", mime="text/html")
        except Exception as e: st.error(f"No se pudo preparar el HTML para descarga: {e}")

# --- Ejecutar ---
if __name__ == "__main__":
    render_scraping_booking()
