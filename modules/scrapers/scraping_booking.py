import streamlit as st
import asyncio
import json
import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# ════════════════════════════════════════════════════
# 📅 Scraping Booking con Playwright (Versión Simple Refactorizada)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright_simple(url: str, browser_instance):
    """Obtiene datos de una URL de Booking usando una instancia de navegador Playwright.
       SIN bloqueo de recursos y SIN lógica de proxy en esta función."""
    html = ""
    page = None
    resultado_final = {}
    
    try:
        page = await browser_instance.new_page(ignore_https_errors=True)
        
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8" 
        })
        
        # print(f"Navegando a: {url} (Playwright modo simple)") # Eliminado por limpieza
        await page.goto(url, timeout=100000, wait_until="domcontentloaded") 
        
        try:
            selector_estable = "#hp_hotel_name" # ¡Verifica y ajusta este selector!
            # print(f"Esperando selector estable: '{selector_estable}' para {url}") # Eliminado
            await page.wait_for_selector(selector_estable, state="visible", timeout=40000)
            # print(f"Selector estable encontrado para {url}.") # Eliminado
        except PlaywrightTimeoutError:
            print(f"Advertencia: Selector estable '{selector_estable}' no encontrado en 40s para {url}. El HTML podría ser incompleto.")
        
        await page.wait_for_timeout(2000) # Pequeña espera fija, mantenida por ahora
        
        html = await page.content()
        # print(f"HTML obtenido para {url} (Tamaño: {len(html)} bytes).") # Eliminado
        
        if not html:
            print(f"Error: HTML vacío para {url}.")
            return {"error": "Fallo_HTML_Vacio_Playwright", "url_original": url, "details": "No se obtuvo contenido HTML."}, ""
        
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url)
        
    except PlaywrightTimeoutError as e:
        details = str(e); print(f"Timeout de Playwright para {url}: {details}")
        error_key = "Fallo_Timeout_PageGoto_Playwright" if "page.goto" in details.lower() else "Fallo_Timeout_Playwright"
        return {"error": error_key, "url_original": url, "details": details}, ""
    except Exception as e:
        error_type = type(e).__name__; details = str(e)
        print(f"Error ({error_type}) procesando {url} con Playwright: {details}")
        error_key = "Fallo_PageContent_Inestable_Playwright" if "page is navigating" in details else f"Fallo_Excepcion_Playwright_{error_type}"
        return {"error": error_key, "url_original": url, "details": details}, ""
    finally:
        if page:
            try: 
                await page.close()
            except Exception as e: 
                print(f"Error menor al cerrar página {url}: {e}")
            
    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (Misma lógica, todos los campos)
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
                except json.JSONDecodeError: 
                    # print(f"Advertencia: Script JSON-LD no pudo ser decodificado en {url}")
                    continue
        # if not data_extraida: print(f"Advertencia: No se encontró JSON-LD tipo Hotel en {url}") # Puede ser verboso
    except Exception as e: print(f"Error general extrayendo JSON-LD para {url}: {e}")
    
    try: 
        scripts_json = soup.find_all('script', type='application/json')
        found_urls_img = set()
        for script in scripts_json:
            if script.string and ('large_url' in script.string or '"url_max300"' in script.string):
                try:
                    data_json = json.loads(script.string); stack = [data_json]
                    while stack and len(imagenes_secundarias) < 15: # Límite de 15 imágenes
                        current = stack.pop()
                        if isinstance(current, dict):
                            for k, v in current.items():
                                if k in ('large_url','url_max1280','url_original') and isinstance(v,str) and v.startswith('https://') and '.staticflickr.com' not in v:
                                    if v not in found_urls_img: 
                                        imagenes_secundarias.append(v); found_urls_img.add(v)
                                elif isinstance(v, (dict, list)): stack.append(v)
                        elif isinstance(current, list): stack.extend(reversed(current)) # Para mantener orden original si importa
                except json.JSONDecodeError: 
                    # print(f"Advertencia: Script JSON de imágenes no pudo ser decodificado en {url}")
                    continue
        for img_tag in soup.find_all("img"): 
            src = img_tag.get("src")
            if src and src.startswith("https://cf.bstatic.com") and src not in found_urls_img and len(imagenes_secundarias) < 15 :
                 imagenes_secundarias.append(src); found_urls_img.add(src)
        # if imagenes_secundarias: print(f"Se encontraron {len(imagenes_secundarias)} URLs de imágenes para {url}")
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
        # if servicios: print(f"Se encontraron {len(servicios)} servicios para {url}")
    except Exception as e: print(f"Error general extrayendo servicios para {url}: {e}")

    titulo_h1_tag = soup.find("h1")
    titulo_h1 = titulo_h1_tag.get_text(strip=True) if titulo_h1_tag else data_extraida.get("name", "")
    # if not titulo_h1: print(f"Advertencia: No se encontró H1 para {url}")
    
    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
    address_info = data_extraida.get("address", {}); rating_info = data_extraida.get("aggregateRating", {})
    
    return {
        "url_original": url, "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "metodo_extraccion": "Playwright_Simple_Refactorizado",
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
# 🗂️ Procesar Lote con Playwright (Versión Simple Refactorizada)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote_simple(urls_a_procesar):
    """Procesa URLs con Playwright, SIN proxy y SIN bloqueo de recursos."""
    tasks_results = []
    browser_launch_options = {"headless": True} 

    # print("Configurando lote Playwright para ejecutarse SIN proxy y SIN bloqueo de recursos.") # Verboso
    
    async with async_playwright() as p:
        browser = None
        try:
            # print("Lanzando navegador Playwright (modo simple)...") # Verboso
            browser = await p.chromium.launch(**browser_launch_options)
            # print("Navegador Playwright lanzado.") # Verboso
            
            tasks = [obtener_datos_booking_playwright_simple(url, browser) for url in urls_a_procesar]
            results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
            
            temp_results = []
            for i, res_or_exc in enumerate(results_with_exceptions):
                url_p = urls_a_procesar[i] # Asegurar que tenemos la URL correcta
                if isinstance(res_or_exc, Exception):
                    print(f"Excepción en gather (Playwright Simple) para {url_p}: {res_or_exc}")
                    temp_results.append({"error": "Fallo_Excepcion_Gather_Playwright_Simple", "url_original": url_p, "details": str(res_or_exc)})
                elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                    res_dict, html_content = res_or_exc
                    if isinstance(res_dict, dict):
                        temp_results.append(res_dict)
                        if not res_dict.get("error") and html_content:
                            st.session_state.last_successful_html_content = html_content
                    else: # res_dict no es un diccionario como se esperaba
                        temp_results.append({"error": "Fallo_TipoResultadoInesperado_Playwright_Simple", "url_original": url_p, "details": f"Se esperaba dict, se obtuvo: {type(res_dict)}"})
                else: # res_or_exc no es ni Excepción ni la tupla esperada
                    temp_results.append({"error": "Fallo_ResultadoInesperado_Playwright_Simple", "url_original": url_p, "details": f"Formato de resultado no reconocido: {type(res_or_exc)}"})
            tasks_results = temp_results
        except Exception as batch_error:
            print(f"Error crítico lote (Playwright Simple): {batch_error}")
            # Asegurar que devolvemos una lista de diccionarios para consistencia
            tasks_results = [{"error": "Fallo_Critico_Lote_Playwright_Simple", "url_original": "Lote Completo", "details": str(batch_error)}]
        finally:
            if browser: 
                await browser.close()
                # print("Navegador Playwright compartido cerrado.") # Verboso
    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (Súper Simplificada)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renderiza la interfaz súper simplificada, usando Playwright sin optimizaciones."""
    st.session_state.setdefault("_called_script", "scraping_booking_playwright_simple_refactor")
    st.title("🏨 Scraping Hoteles Booking (Playwright Simple - Refactorizado)")
    st.caption("Modo simple: Usa Playwright sin proxy y sin bloqueo de recursos.")

    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales_simple", [])
    st.session_state.setdefault("last_successful_html_content", "")
    
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150,
        placeholder="Ej: https://www.booking.com/hotel/es/nombre-hotel.es.html"
    )
    
    col1, col2 = st.columns([1, 3]) # Mantener un layout similar
    with col1:
        buscar_btn = st.button("🔍 Scrapear (Simple)", use_container_width=True) # Botón actualizado

    if buscar_btn:
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.strip() and "booking.com/hotel" in url.strip()]
        if not urls: 
            st.warning("Introduce URLs válidas de Booking.com.")
            st.stop()

        st.session_state.last_successful_html_content = "" 
        with st.spinner(f"Procesando {len(urls)} URLs con Playwright (modo simple)..."):
            resultados_actuales = asyncio.run(procesar_urls_en_lote_simple(urls))
        
        st.session_state.resultados_finales_simple = resultados_actuales
        st.rerun()

    if st.session_state.resultados_finales_simple:
        st.markdown("---")
        st.subheader("📊 Resultados Finales (Playwright Simple)")
        
        resultados = st.session_state.resultados_finales_simple
        num_exitos = sum(1 for r in resultados if isinstance(r, dict) and not r.get("error"))
        num_fallos = len(resultados) - num_exitos
        
        st.write(f"Procesados: {len(resultados)} | Éxitos: {num_exitos} | Fallos: {num_fallos}")
        
        with st.expander("Ver resultados detallados (JSON)", expanded=(num_fallos > 0)):
             st.json(resultados)

    if st.session_state.last_successful_html_content:
        st.markdown("---")
        st.subheader("📄 Último HTML Capturado con Éxito")
        try:
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(label="⬇️ Descargar HTML", data=html_bytes,
                file_name="ultimo_hotel_booking_playwright_simple.html", mime="text/html")
        except Exception as e: 
            st.error(f"No se pudo preparar el HTML para descarga: {e}")

# --- Ejecutar ---
if __name__ == "__main__":
    render_scraping_booking()
