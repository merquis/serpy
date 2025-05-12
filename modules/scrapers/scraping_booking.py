import streamlit as st
import asyncio
import json
import datetime
# import requests # Ya no es necesario
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# Importaciones locales (comentadas si no se usan aquí directamente)
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
# Nota: Las funciones de drive_utils no se llaman en este script específico.

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData (Simplificada)
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
            return {
                "server": f"{host}:{port}",
                "username": username,
                "password": password
            }
        else:
            # La UI informará si esto devuelve None
            return None
    except KeyError:
         # La UI informará si esto devuelve None
        return None
    except Exception as e:
        print(f"Error inesperado leyendo configuración proxy: {e}")
        return None

# ════════════════════════════════════════════════════
# 📅 Scraping Booking (Función Principal Optimizada)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance):
    """
    Obtiene datos de una URL de Booking usando una instancia de navegador ya configurada.
    Optimizado para bloquear recursos innecesarios.
    Args:
        url (str): La URL del hotel.
        browser_instance: La instancia del navegador Playwright (debe estar ya lanzada con proxy).
    Returns:
        tuple: (dict_resultados, html_content) o (dict_error, "")
    """
    html = ""
    page = None
    resultado_final = {}

    try:
        page = await browser_instance.new_page(
            ignore_https_errors=True # Ignorar errores SSL comunes con proxies
        )

        # --- OPTIMIZACIÓN: Bloquear Recursos Innecesarios ---
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
        # Puedes ajustar los tipos a bloquear: "image", "stylesheet", "font", "script", "media", "websocket", etc.
        # Bloquear "script" es arriesgado, puede romper la carga de datos dinámicos.
        # --- Fin Optimización ---


        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        # --- Navegación y Scraping ---
        print(f"Navegando (con bloqueo de recursos) a: {url}")
        await page.goto(url, timeout=90000, wait_until="load") # 'load' espera más que 'domcontentloaded'

        # --- ESPERA ROBUSTA (¡Importante!) ---
        try:
            # Esperar a que un elemento clave esté visible.
            # ¡¡VERIFICA Y AJUSTA ESTE SELECTOR!! Ej: "#hp_hotel_name"
            selector_estable = "#hp_hotel_name"
            print(f"Esperando selector estable: '{selector_estable}'")
            await page.wait_for_selector(selector_estable, state="visible", timeout=30000)
            print("Selector estable encontrado.")
        except PlaywrightTimeoutError:
            print(f"Advertencia: No se encontró el selector estable '{selector_estable}' en 30s para {url}. Puede que falten datos.")
            # Continuar de todas formas, quizás el HTML básico sirva

        # --- Obtener HTML ---
        print("Intentando obtener page.content()...")
        html = await page.content()
        print(f"HTML obtenido para {url} (Tamaño: {len(html)} bytes)")

        if not html:
            print(f"Advertencia: El contenido HTML está vacío para {url}.")
            return {"error": "HTML vacío", "url_original": url, "details": "No se pudo obtener contenido HTML."}, ""

        # --- Parseo ---
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url) # Llama a la función de parseo

    except PlaywrightTimeoutError as e:
        details = str(e)
        print(f"Timeout de Playwright para {url}: {details}")
        if "page is navigating and changing the content" in details:
             return {"error": "Error Page.content (Página inestable)", "url_original": url, "details": details}, ""
        else:
             return {"error": "Timeout de Playwright", "url_original": url, "details": details}, ""
    except Exception as e:
        error_type = type(e).__name__
        details = str(e)
        print(f"Error ({error_type}) procesando {url}: {details}")
        if "page is navigating and changing the content" in details:
             return {"error": "Error Page.content (Página inestable)", "url_original": url, "details": details}, ""
        else:
             return {"error": f"Error en Playwright/Scraping ({error_type})", "url_original": url, "details": details}, ""
    finally:
        if page:
            try:
                await page.close()
            except Exception as page_close_error:
                print(f"Error menor al cerrar página para {url}: {page_close_error}")

    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (Limpio, sin IPs)
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    """Parsea el HTML (BeautifulSoup) y extrae datos del hotel."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Extraer parámetros de búsqueda de la URL
    group_adults = query_params.get('group_adults', [''])[0]
    group_children = query_params.get('group_children', [''])[0]
    no_rooms = query_params.get('no_rooms', [''])[0]
    checkin_year_month_day = query_params.get('checkin', [''])[0]
    checkout_year_month_day = query_params.get('checkout', [''])[0]
    dest_type = query_params.get('dest_type', [''])[0]

    data_extraida = {}
    imagenes_secundarias = []
    servicios = []

    # Extraer JSON-LD
    try:
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string)
                    potential_hotels = []
                    if isinstance(data_json, list): potential_hotels.extend(data_json)
                    elif isinstance(data_json, dict): potential_hotels.append(data_json)
                    for item in potential_hotels:
                        if isinstance(item, dict) and item.get("@type") == "Hotel":
                            data_extraida = item
                            break
                    if data_extraida: break
                except json.JSONDecodeError: continue
    except Exception as e:
        print(f"Error extrayendo JSON-LD: {e}")

    # Extraer Imágenes de scripts application/json
    try:
        scripts_json = soup.find_all('script', type='application/json')
        for script in scripts_json:
            if script.string and ('large_url' in script.string or '"url_max300"' in script.string):
                try:
                    data_json = json.loads(script.string)
                    stack = [data_json]; found_urls = set()
                    while stack and len(imagenes_secundarias) < 15:
                        current = stack.pop()
                        if isinstance(current, dict):
                            for key, value in current.items():
                                if key in ('large_url', 'url_max1280', 'url_original') and isinstance(value, str) and value.startswith('https://') and '.staticflickr.com' not in value:
                                    if value not in found_urls:
                                        imagenes_secundarias.append(value); found_urls.add(value)
                                elif isinstance(value, (dict, list)):
                                    stack.append(value)
                        elif isinstance(current, list): stack.extend(reversed(current))
                except json.JSONDecodeError: continue
    except Exception as e:
        print(f"Error extrayendo imágenes de JSON: {e}")

    # Extraer Servicios
    possible_service_classes = ["hotel-facilities__list", "facilitiesChecklistSection", "hp_desc_important_facilities", "bui-list__description", "db29ecfbe2"] # Ejemplos
    servicios_set = set()
    try:
        for class_name in possible_service_classes:
             containers = soup.find_all(class_=class_name)
             for container in containers:
                  items = container.find_all(['li', 'span', 'div'], recursive=True)
                  for item in items:
                       texto = item.get_text(strip=True)
                       if texto and len(texto) > 3 and 'icono' not in texto.lower() and 'mostrar' not in texto.lower():
                           servicios_set.add(texto)
        servicios = sorted(list(servicios_set))
    except Exception as e:
        print(f"Error extrayendo servicios: {e}")

    # Extraer Títulos H1 y H2
    titulo_h1 = soup.find("h1").get_text(strip=True) if soup.find("h1") else data_extraida.get("name", "")
    bloques_contenido_h2 = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]

    # Construir el diccionario final (sin IPs)
    address_info = data_extraida.get("address", {})
    rating_info = data_extraida.get("aggregateRating", {})

    return {
        # Metadatos del scraping
        "url_original": url,
        "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),

        # Parámetros de búsqueda (si se encontraron en la URL)
        "busqueda_checkin": checkin_year_month_day,
        "busqueda_checkout": checkout_year_month_day,
        "busqueda_adultos": group_adults,
        "busqueda_ninos": group_children,
        "busqueda_habitaciones": no_rooms,
        "busqueda_tipo_destino": dest_type,

        # Datos del Hotel (extraídos)
        "nombre_alojamiento": data_extraida.get("name", titulo_h1),
        "tipo_alojamiento": data_extraida.get("@type", "Desconocido"),
        "direccion": address_info.get("streetAddress"),
        "codigo_postal": address_info.get("postalCode"),
        "ciudad": address_info.get("addressLocality"),
        "pais": address_info.get("addressCountry"),
        "latitud": data_extraida.get("geo", {}).get("latitude"),
        "longitud": data_extraida.get("geo", {}).get("longitude"),
        "url_hotel_booking": data_extraida.get("url"),
        "descripcion_corta": data_extraida.get("description"),
        "valoracion_global": rating_info.get("ratingValue"),
        "mejor_valoracion_posible": rating_info.get("bestRating", "10"),
        "numero_opiniones": rating_info.get("reviewCount"),
        "rango_precios": data_extraida.get("priceRange"),

        # Contenido extraído
        "titulo_h1": titulo_h1,
        "subtitulos_h2": bloques_contenido_h2,
        "servicios_principales": servicios,
        "imagenes": imagenes_secundarias,
        "errores_parseo": [] # Podría llenarse si fallan partes del parseo
    }


# ════════════════════════════════════════════════════
# 🗂️ Procesar varias URLs en lote (Optimizado)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar):
    """Procesa una lista de URLs usando un navegador compartido con proxy."""
    tasks_results = []
    proxy_conf = get_proxy_settings()

    if not proxy_conf:
        return [{"error": "Configuración de proxy no disponible", "url_original": None, "details": "Verifica st.secrets[brightdata_booking]"}]

    async with async_playwright() as p:
        browser = None # Definir fuera del try para el finally
        try:
            print("Lanzando navegador compartido CON proxy...")
            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy_conf
            )
            print(f"Navegador lanzado con proxy: {proxy_conf['server']}")

            # Crear tareas sin verificación de IP explícita
            tasks = [obtener_datos_booking_playwright(url, browser) for url in urls_a_procesar]

            results_with_html = await asyncio.gather(*tasks, return_exceptions=True)

            # Procesar resultados
            st.session_state.last_successful_html_content = "" # Resetear
            for i, res_or_exc in enumerate(results_with_html):
                url_procesada = urls_a_procesar[i]
                if isinstance(res_or_exc, Exception):
                    print(f"Excepción en gather para {url_procesada}: {res_or_exc}")
                    tasks_results.append({"error": "Excepción en asyncio.gather", "url_original": url_procesada, "details": str(res_or_exc)})
                elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                    resultado_item, html_content_item = res_or_exc
                    if isinstance(resultado_item, dict):
                         tasks_results.append(resultado_item)
                         if not resultado_item.get("error") and html_content_item:
                             st.session_state.last_successful_html_content = html_content_item
                    else:
                         tasks_results.append({"error": "Resultado inesperado (no dict)", "url_original": url_procesada,"details": f"Tipo: {type(resultado_item)}"})
                else:
                    tasks_results.append({"error": "Resultado inesperado de tarea", "url_original": url_procesada, "details": str(res_or_exc)})

        except Exception as batch_error:
            print(f"Error crítico durante el procesamiento del lote: {batch_error}")
            if not tasks_results: # Añadir error solo si no hay resultados previos
                 tasks_results.append({"error": "Error crítico en procesar_urls_en_lote", "url_original": None, "details": str(batch_error)})
        finally:
            if browser:
                await browser.close()
                print("Navegador compartido cerrado.")

    return tasks_results


# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (Simplificada)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renderiza la interfaz de Streamlit simplificada."""
    st.session_state.setdefault("_called_script", "scraping_booking")
    st.title("🏨 Scraping Hoteles Booking (Optimizado)")

    # Inicializar estado
    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_json", [])
    st.session_state.setdefault("last_successful_html_content", "")

    # Comprobar configuración proxy
    proxy_settings = get_proxy_settings()
    proxy_ok = proxy_settings is not None
    if not proxy_ok:
        st.error("🚨 ¡Configuración del Proxy NO encontrada o incompleta en st.secrets! Verifica `[brightdata_booking]` en `secrets.toml`.")

    # --- UI ---
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150,
        placeholder="Ej: https://www.booking.com/hotel/es/nombre-hotel.es.html"
    )

    col1, col2 = st.columns([1, 3]) # Ajustar columnas
    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles", disabled=(not proxy_ok), use_container_width=True)

    # --- Lógica de Scraping ---
    if buscar_btn:
        # No llamamos a detectar_ip_real()
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.strip() and "booking.com/hotel" in url.strip()]

        if not urls:
            st.warning("Por favor, introduce URLs válidas de hoteles de Booking.com.")
        else:
            with st.spinner(f"Scrapeando {len(urls)} hoteles... (Bloqueando imágenes/css/fuentes)"):
                resultados = asyncio.run(procesar_urls_en_lote(urls))
                st.session_state.resultados_json = resultados
            st.rerun()

    # --- Mostrar Resultados ---
    if st.session_state.resultados_json:
        st.markdown("---")
        st.subheader("📊 Resultados")

        # Ya no mostramos la verificación de IP

        # Resumen rápido
        num_exitos = sum(1 for r in st.session_state.resultados_json if isinstance(r, dict) and not r.get("error"))
        num_fallos = len(st.session_state.resultados_json) - num_exitos
        st.write(f"Procesados: {len(st.session_state.resultados_json)} | Éxitos: {num_exitos} | Fallos: {num_fallos}")

        # Mostrar JSON de resultados detallados
        with st.expander("Ver resultados detallados (JSON)", expanded=(num_fallos > 0)): # Expandir si hay fallos
             st.json(st.session_state.resultados_json)


    # --- Descarga de HTML ---
    if st.session_state.last_successful_html_content:
        st.markdown("---")
        st.subheader("📄 Último HTML Capturado con Éxito")
        try:
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(
                label="⬇️ Descargar HTML",
                data=html_bytes,
                file_name="ultimo_hotel_booking.html",
                mime="text/html"
            )
        except Exception as e:
            st.error(f"No se pudo preparar el HTML para descarga: {e}")


# --- Ejecutar la función de renderizado ---
if __name__ == "__main__":
    render_scraping_booking()
