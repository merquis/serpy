import streamlit as st
import asyncio
import json
import datetime
import httpx # Biblioteca para hacer requests HTTP asíncronos
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
# import copy # No parece usarse explícitamente, se puede omitir

# Importaciones locales (comentadas si no se usan aquí directamente)
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
# Nota: Las funciones de drive_utils no se llaman en este script específico.

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData
# ════════════════════════════════════════════════════
def get_proxy_settings():
    """Lee la configuración del proxy desde st.secrets y la formatea para HTTPX."""
    try:
        proxy_config = st.secrets["brightdata_booking"]
        host = proxy_config.get("host")
        port = proxy_config.get("port")
        username = proxy_config.get("username")
        password = proxy_config.get("password")
        if host and port and username and password:
            # Formato para httpx (asumiendo proxy HTTP/HTTPS)
            proxy_url = f"http://{username}:{password}@{host}:{port}"
            return {"http://": proxy_url, "https://": proxy_url}
        else:
            print("Advertencia: Faltan datos en la configuración del proxy en st.secrets.")
            return None
    except KeyError:
        print("Advertencia: No se encontró la sección [brightdata_booking] en st.secrets.")
        return None
    except Exception as e:
        print(f"Error inesperado leyendo configuración proxy: {e}")
        return None

# ════════════════════════════════════════════════════
# 📅 Scraping Booking con HTTPX (Proxy en CONSTRUCTOR)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_httpx(url: str, httpx_proxy_config: dict = None):
    """Obtiene HTML de una URL usando HTTPX (SIN ejecución de JavaScript).
       El proxy se pasa al CONSTRUCTOR de AsyncClient."""
    html = ""
    resultado_final = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Connection": "keep-alive"
    }

    try:
        print(f"Intentando obtener HTML para {url} con HTTPX {'CON' if httpx_proxy_config else 'SIN'} proxy...")
        
        # --- Proxy se pasa al constructor de AsyncClient ---
        # http2=True quitado temporalmente para simplificar la depuración del proxy
        async with httpx.AsyncClient(
            proxies=httpx_proxy_config, 
            follow_redirects=True
            # http2=True # Puedes reactivar si tienes httpx[http2] bien instalado
        ) as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status() 
            html = response.text
        
        print(f"HTML obtenido para {url} con HTTPX (Tamaño: {len(html)} bytes)")

        if not html or len(html) < 200: # Umbral bajo, esperando HTML mínimo
            print(f"Error: HTML vacío o extremadamente pequeño para {url}.")
            return {"error": "Fallo_HTML_Minimo_HTTPX", "url_original": url, "details": f"Tamaño HTML: {len(html)}"}, ""
        
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url) 
        
    except httpx.HTTPStatusError as e:
        details = f"Error HTTP {e.response.status_code} para {url}: {e.response.text[:200]}"
        print(details)
        return {"error": f"Fallo_HTTPX_Status_{e.response.status_code}", "url_original": url, "details": details}, ""
    except httpx.RequestError as e:
        details = str(e)
        print(f"Error de red con HTTPX para {url}: {details}")
        return {"error": "Fallo_HTTPX_RequestError", "url_original": url, "details": details}, ""
    except TypeError as e: # Captura específica por si el error de 'proxies' persiste
        details = str(e)
        print(f"TypeError procesando {url} con HTTPX (posible problema de versión/entorno): {details}")
        return {"error": "Fallo_Excepcion_HTTPX_TypeError_Constructor", "url_original": url, "details": details}, ""
    except Exception as e:
        error_type = type(e).__name__; details = str(e)
        print(f"Error ({error_type}) procesando {url} con HTTPX: {details}")
        return {"error": f"Fallo_Excepcion_HTTPX_{error_type}", "url_original": url, "details": details}, ""
        
    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (espera HTML muy básico)
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    """Parsea el HTML (BeautifulSoup) y extrae datos del hotel.
       Con HTTPX, muchos datos dinámicos probablemente faltarán."""
    parsed_url = urlparse(url); query_params = parse_qs(parsed_url.query)
    group_adults = query_params.get('group_adults', [''])[0]
    group_children = query_params.get('group_children', [''])[0]
    no_rooms = query_params.get('no_rooms', [''])[0]
    checkin_year_month_day = query_params.get('checkin', [''])[0]
    checkout_year_month_day = query_params.get('checkout', [''])[0]
    dest_type = query_params.get('dest_type', [''])[0]
    data_extraida, imagenes_secundarias, servicios = {}, [], []
    
    print(f"Parseando HTML para {url} (obtenido con HTTPX, probablemente sin JS)...")

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
                    if data_extraida: print(f"JSON-LD encontrado para {url} (puede estar incompleto)"); break
                except: continue
        if not data_extraida: print(f"Advertencia: No se encontró JSON-LD para Hotel en {url}")
    except Exception as e: print(f"Error extrayendo JSON-LD: {e}")
    
    try: # Imágenes: Buscar en etiquetas <img>
        found_urls_img = set() # Para evitar duplicados al buscar en etiquetas img
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if src and src.startswith("https://cf.bstatic.com") and src not in found_urls_img and len(imagenes_secundarias) < 15 :
                 imagenes_secundarias.append(src)
                 found_urls_img.add(src)
        if imagenes_secundarias: print(f"Se encontraron {len(imagenes_secundarias)} URLs de imágenes en etiquetas <img> para {url}")
    except Exception as e: print(f"Error extrayendo imágenes de <img>: {e}")

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
    if titulo_h1: print(f"Título H1 encontrado para {url}: {titulo_h1[:50]}...")
    else: print(f"Advertencia: No se encontró H1 para {url}")

    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
    if h2s: print(f"Se encontraron {len(h2s)} H2s para {url}")

    address_info = data_extraida.get("address", {}); rating_info = data_extraida.get("aggregateRating", {})
    return {
        "url_original": url, "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "metodo_extraccion": "HTTPX",
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
# 🗂️ Procesar Lote con HTTPX
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote_httpx(urls_a_procesar, use_proxy: bool):
    """Procesa URLs con HTTPX, CON o SIN proxy según se indique."""
    tasks_results = []
    httpx_proxy_config_para_pasar = None 

    if use_proxy:
        proxy_settings_direct = get_proxy_settings() 
        if not proxy_settings_direct:
            print("Error: Se requiere proxy pero no está configurado en st.secrets.")
            return [{"error": "Proxy requerido pero no configurado", "url_original": url, "details": ""} for url in urls_a_procesar]
        else:
            httpx_proxy_config_para_pasar = proxy_settings_direct
            print(f"Configurando lote HTTPX para usar proxy: {httpx_proxy_config_para_pasar.get('http://', 'No definido')}")
    else:
        print("Configurando lote HTTPX para ejecutarse SIN proxy.")
    
    tasks = [obtener_datos_booking_httpx(url, httpx_proxy_config_para_pasar) for url in urls_a_procesar]
    results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
    
    temp_results = []
    for i, res_or_exc in enumerate(results_with_exceptions):
        url_p = urls_a_procesar[i]
        if isinstance(res_or_exc, Exception):
            print(f"Excepción en gather (HTTPX) para {url_p}: {res_or_exc}")
            temp_results.append({"error": "Fallo_Excepcion_Gather_HTTPX", "url_original": url_p, "details": str(res_or_exc)})
        elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
            res_dict, html_content = res_or_exc
            if isinstance(res_dict, dict):
                temp_results.append(res_dict)
                if not res_dict.get("error") and html_content:
                     st.session_state.last_successful_html_content = html_content
            else:
                temp_results.append({"error": "Fallo_TipoResultadoInesperado_HTTPX", "url_original": url_p, "details": f"Tipo: {type(res_dict)}"})
        else:
            temp_results.append({"error": "Fallo_ResultadoInesperado_HTTPX", "url_original": url_p, "details": str(res_or_exc)})
    tasks_results = temp_results
    
    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (adaptada para HTTPX)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renderiza la interfaz, usando HTTPX para el intento sin proxy."""
    st.session_state.setdefault("_called_script", "scraping_booking_httpx")
    st.title("🏨 Scraping Hoteles Booking (HTTPX v3)")
    st.caption("Este modo usa HTTPX (1 request, sin JS) para el primer intento sin proxy.")

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
        "Usar proxy directamente para todos los intentos (con HTTPX)",
        value=st.session_state.force_proxy_checkbox, disabled=(not proxy_ok),
        help="Si se marca, todas las URLs se procesarán con HTTPX y proxy. Si no, se intentará con HTTPX sin proxy, y los fallos se reintentarán con HTTPX y proxy."
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear con HTTPX", use_container_width=True)

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
            with st.spinner(f"Procesando {len(urls)} URLs directamente CON proxy (usando HTTPX)..."):
                resultados_actuales = asyncio.run(procesar_urls_en_lote_httpx(urls, use_proxy=True))
        else: 
            final_results_map = {}
            with st.spinner(f"Paso 1/2: Intentando {len(urls)} URLs SIN proxy (usando HTTPX)..."):
                results_pass_1 = asyncio.run(procesar_urls_en_lote_httpx(urls, use_proxy=False))

            urls_a_reintentar = []
            for i, result in enumerate(results_pass_1):
                url = urls[i]
                final_results_map[url] = result
                if isinstance(result, dict) and result.get("error"): urls_a_reintentar.append(url)
                elif not isinstance(result, dict):
                    urls_a_reintentar.append(url)
                    final_results_map[url] = {"error":"Fallo_FormatoInvalidoP1_HTTPX", "url_original":url, "details":"Resultado no fue diccionario"}

            if urls_a_reintentar:
                st.info(f"{len(urls_a_reintentar)} URL(s) fallaron sin proxy (HTTPX). Preparando reintento con proxy (HTTPX)...")
                if not proxy_ok:
                    st.error("Proxy no configurado. No se pueden reintentar las URLs fallidas con proxy.")
                else:
                    with st.spinner(f"Paso 2/2: Reintentando {len(urls_a_reintentar)} URL(s) CON proxy (usando HTTPX)..."):
                        results_pass_2 = asyncio.run(procesar_urls_en_lote_httpx(urls_a_reintentar, use_proxy=True))
                    for i, result_retry in enumerate(results_pass_2):
                        url_retry = urls_a_reintentar[i]
                        if isinstance(result_retry, dict):
                            result_retry["nota"] = "Resultado tras reintento con proxy (HTTPX)"
                            final_results_map[url_retry] = result_retry
                        else:
                            final_results_map[url_retry] = {"error":"Fallo_FormatoInvalidoP2_HTTPX", "url_original":url_retry, "details":"Resultado reintento no fue diccionario"}
            elif not forzar_proxy_directo :
                st.success("¡Todas las URLs se procesaron con éxito sin proxy (usando HTTPX)!")
            
            resultados_actuales = [final_results_map[url] for url in urls]

        st.session_state.resultados_finales = resultados_actuales
        st.rerun()

    if st.session_state.resultados_finales:
        st.markdown("---"); st.subheader("📊 Resultados Finales (HTTPX)")
        num_exitos = sum(1 for r in st.session_state.resultados_finales if isinstance(r, dict) and not r.get("error"))
        num_fallos = len(st.session_state.resultados_finales) - num_exitos
        st.write(f"Procesados: {len(st.session_state.resultados_finales)} | Éxitos: {num_exitos} | Fallos: {num_fallos}")
        with st.expander("Ver resultados detallados (JSON)", expanded=(num_fallos > 0)):
             st.json(st.session_state.resultados_finales)

    if st.session_state.last_successful_html_content:
        st.markdown("---"); st.subheader("📄 Último HTML Capturado con Éxito (HTTPX)")
        try:
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(label="⬇️ Descargar HTML", data=html_bytes,
                file_name="ultimo_hotel_booking_httpx.html", mime="text/html")
        except Exception as e: st.error(f"No se pudo preparar el HTML para descarga: {e}")

if __name__ == "__main__":
    render_scraping_booking()
