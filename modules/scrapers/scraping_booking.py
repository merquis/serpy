import streamlit as st
import asyncio
import json
import datetime
import httpx # Biblioteca para hacer requests HTTP asíncronos
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
# import copy # No se usa explícitamente en esta versión

# Importaciones locales (comentadas si no se usan aquí directamente)
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData (adaptado para transport)
# ════════════════════════════════════════════════════
def get_proxy_url_for_transport(): # Nombre cambiado para claridad
    """Lee la configuración del proxy y devuelve solo la URL formateada para transport."""
    try:
        proxy_config = st.secrets["brightdata_booking"]
        host = proxy_config.get("host")
        port = proxy_config.get("port")
        username = proxy_config.get("username")
        password = proxy_config.get("password")
        if host and port and username and password:
            # Formato de URL de proxy completa
            return f"http://{username}:{password}@{host}:{port}"
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
# 📅 Scraping Booking con HTTPX (Usando AsyncHTTPTransport para Proxy)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_httpx(url: str, proxy_url_for_transport: str = None):
    """Obtiene HTML de una URL usando HTTPX, configurando proxy vía AsyncHTTPTransport."""
    html = ""
    resultado_final = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Connection": "keep-alive"
    }

    # Crear el transporte
    transport = None
    if proxy_url_for_transport:
        try:
            # Para httpx >= 0.20.0, AsyncHTTPTransport toma un httpx.Proxy
            # Para versiones más antiguas, podría ser directamente proxy_url en algunos casos,
            # pero el error sugiere que la API de `proxies` en AsyncClient es el problema.
            # La imagen que mostraste dice: transport=httpx.AsyncHTTPTransport(proxy_url=...)
            # o transport=httpx.HTTPTransport(proxy_url=...)
            # Vamos a intentar con AsyncHTTPTransport y pasando un objeto Proxy, que es más estándar para versiones
            # que sí usan transport para esto. Si la imagen se refiere a una versión muy específica,
            # podríamos necesitar ajustar esto.
            # Por ahora, intentaremos la forma más compatible si `proxies` en AsyncClient no funciona.
            #
            # Según la imagen, parece ser más bien:
            # transport = httpx.AsyncHTTPTransport(proxy=proxy_url_for_transport) # Esto no es estándar para proxy URL
            # o
            # transport = httpx.AsyncHTTPTransport(proxies={"all://": proxy_url_for_transport}) # Más parecido a la config de proxies
            #
            # La documentación de httpx para versiones que usan 'transport' para proxies
            # usualmente implica crear un httpx.Proxy primero
            # Ejemplo: proxy_object = httpx.Proxy(url=proxy_url_for_transport)
            #          transport = httpx.AsyncHTTPTransport(proxy=proxy_object)
            #
            # Vamos a seguir la sugerencia de tu imagen lo más literal posible:
            # Asumiré que proxy_url_for_transport es la URL completa del proxy.
            # La imagen dice "...transport=httpx.AsyncHTTPTransport(proxy_url=...)"
            # Aunque 'proxy_url' no es un argumento estándar de AsyncHTTPTransport,
            # sí lo es de httpx.Proxy().
            # Y AsyncHTTPTransport SÍ toma un argumento 'proxy' que espera un objeto Proxy.
            #
            # Intento 1: Siguiendo la sugerencia de la imagen, aunque 'proxy_url' no es un arg directo de AsyncHTTPTransport
            # Esto probablemente dará error si 'proxy_url' no es un argumento válido.
            # transport = httpx.AsyncHTTPTransport(proxy_url=proxy_url_for_transport) # Probablemente incorrecto

            # Intento 2: La forma más correcta si se usa transport para proxies es con un objeto httpx.Proxy
            # Esto requiere que `proxy_url_for_transport` sea la URL completa del proxy, ej: "http://user:pass@host:port"
            proxy_obj = httpx.Proxy(proxy_url_for_transport)
            transport = httpx.AsyncHTTPTransport(proxy=proxy_obj)
            print(f"Usando transporte con proxy: {proxy_url_for_transport}")

        except Exception as e_transport:
            print(f"Error configurando el transporte del proxy: {e_transport}")
            return {"error": "Fallo_Config_Transporte_Proxy", "url_original": url, "details": str(e_transport)}, ""
    
    client_args = {"follow_redirects": True}
    if transport:
        client_args["transport"] = transport

    try:
        print(f"Intentando obtener HTML para {url} con HTTPX {'CON TRANSPORTE PROXY' if transport else 'SIN proxy'}...")
        
        async with httpx.AsyncClient(**client_args) as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status() 
            html = response.text
        
        print(f"HTML obtenido para {url} con HTTPX (Tamaño: {len(html)} bytes)")

        if not html or len(html) < 200:
            print(f"Error: HTML vacío o extremadamente pequeño para {url}.")
            return {"error": "Fallo_HTML_Minimo_HTTPX", "url_original": url, "details": f"Tamaño HTML: {len(html)}"}, ""
        
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url) 
        
    # ... (resto de los bloques except y finally se mantienen igual que en la versión anterior) ...
    except httpx.HTTPStatusError as e:
        # ...
    except httpx.RequestError as e:
        # ...
    except TypeError as e: # Captura específica por si el error de 'proxies' persiste
        # ...
    except Exception as e:
        # ...
            
    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (se mantiene igual)
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    # ... (Esta función no necesita cambios) ...
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
                    if data_extraida: print(f"JSON-LD encontrado para {url} (puede estar incompleto)"); break
                except: continue
        if not data_extraida: print(f"Advertencia: No se encontró JSON-LD para Hotel en {url}")
    except Exception as e: print(f"Error extrayendo JSON-LD: {e}")
    try: # Imágenes
        found_urls_img = set()
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
# 🗂️ Procesar Lote con HTTPX (adaptado para transport)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote_httpx(urls_a_procesar, use_proxy: bool):
    """Procesa URLs con HTTPX, configurando proxy vía transport si use_proxy es True."""
    tasks_results = []
    proxy_url_for_transport_to_pass = None

    if use_proxy:
        proxy_url_for_transport_to_pass = get_proxy_url_for_transport() # Obtiene la URL del proxy
        if not proxy_url_for_transport_to_pass:
            print("Error: Se requiere proxy pero no está configurado en st.secrets.")
            return [{"error": "Proxy requerido pero no configurado", "url_original": url, "details": ""} for url in urls_a_procesar]
        else:
            print(f"Configurando lote HTTPX para usar proxy URL (para transport): {proxy_url_for_transport_to_pass}")
    else:
        print("Configurando lote HTTPX para ejecutarse SIN proxy.")
    
    # Pasar la URL del proxy (o None) a cada tarea
    tasks = [obtener_datos_booking_httpx(url, proxy_url_for_transport_to_pass) for url in urls_a_procesar]
    results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
    
    temp_results = []
    # ... (el resto del procesamiento de temp_results se mantiene igual que en la versión anterior) ...
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
# 🎯 Función principal Streamlit (se mantiene igual)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renderiza la interfaz, usando HTTPX y la lógica de dos pasadas con opción de forzar proxy."""
    # ... (Esta función no necesita cambios respecto a la última versión que te di,
    #      ya que llama a procesar_urls_en_lote_httpx, que ahora internamente
    #      pasará el proxy_url a obtener_datos_booking_httpx) ...
    st.session_state.setdefault("_called_script", "scraping_booking_httpx_transport")
    st.title("🏨 Scraping Hoteles Booking (HTTPX + Transport)")
    st.caption("Este modo usa HTTPX (1 request, sin JS) para el primer intento sin proxy. Proxy vía transport.")

    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales", [])
    st.session_state.setdefault("last_successful_html_content", "")
    st.session_state.setdefault("force_proxy_checkbox", False)

    proxy_settings_url = get_proxy_url_for_transport(); proxy_ok = proxy_settings_url is not None
    if not proxy_ok:
        st.warning("⚠️ Proxy no configurado. El modo 'forzar proxy' y los reintentos con proxy no funcionarán.")

    st.session_state.urls_input = st.text_area(
        "📝 URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150,
        placeholder="Ej: https://www.booking.com/hotel/es/nombre-hotel.es.html"
    )
    st.session_state.force_proxy_checkbox = st.checkbox(
        "Usar proxy directamente para todos los intentos (con HTTPX y Transport)",
        value=st.session_state.force_proxy_checkbox, disabled=(not proxy_ok),
        help="Si se marca, todas las URLs se procesarán con HTTPX y proxy (vía transport). Si no, se intentará con HTTPX sin proxy, y los fallos se reintentarán con HTTPX y proxy (vía transport)."
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear con HTTPX (Transport)", use_container_width=True)

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
            with st.spinner(f"Procesando {len(urls)} URLs directamente CON proxy (HTTPX Transport)..."):
                resultados_actuales = asyncio.run(procesar_urls_en_lote_httpx(urls, use_proxy=True))
        else: 
            final_results_map = {}
            with st.spinner(f"Paso 1/2: Intentando {len(urls)} URLs SIN proxy (HTTPX)..."):
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
                st.info(f"{len(urls_a_reintentar)} URL(s) fallaron sin proxy (HTTPX). Preparando reintento con proxy (HTTPX Transport)...")
                if not proxy_ok:
                    st.error("Proxy no configurado. No se pueden reintentar las URLs fallidas con proxy.")
                else:
                    with st.spinner(f"Paso 2/2: Reintentando {len(urls_a_reintentar)} URL(s) CON proxy (HTTPX Transport)..."):
                        results_pass_2 = asyncio.run(procesar_urls_en_lote_httpx(urls_a_reintentar, use_proxy=True))
                    for i, result_retry in enumerate(results_pass_2):
                        url_retry = urls_a_reintentar[i]
                        if isinstance(result_retry, dict):
                            result_retry["nota"] = "Resultado tras reintento con proxy (HTTPX Transport)"
                            final_results_map[url_retry] = result_retry
                        else:
                            final_results_map[url_retry] = {"error":"Fallo_FormatoInvalidoP2_HTTPX", "url_original":url_retry, "details":"Resultado reintento no fue diccionario"}
            elif not forzar_proxy_directo :
                st.success("¡Todas las URLs se procesaron con éxito sin proxy (usando HTTPX)!")
            
            resultados_actuales = [final_results_map[url] for url in urls]

        st.session_state.resultados_finales = resultados_actuales
        st.rerun()

    if st.session_state.resultados_finales:
        st.markdown("---"); st.subheader("📊 Resultados Finales (HTTPX Transport)")
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
