import streamlit as st
import asyncio
import json
import datetime
# import requests # No necesario
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

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
            # Devuelve en formato diccionario
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

# (Funciones de verificación de IP eliminadas)

# ════════════════════════════════════════════════════
# 📅 Scraping Booking (Simplificada: asume que recibe browser)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance):
    """
    Obtiene datos de una URL de Booking usando una instancia de navegador ya configurada.
    Asume que browser_instance ya tiene el proxy configurado si es necesario.
    """
    html = ""
    page = None
    resultado_final = {}

    try:
        # Crear página desde la instancia de navegador proporcionada
        page = await browser_instance.new_page(ignore_https_errors=True)

        # --- Opcional: Bloquear Recursos para Optimizar Requests ---
        # Descomenta esta línea si quieres reducir requests (¡prueba si afecta datos!)
        # await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
        # --- Fin Optimización ---

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        print(f"Navegando a: {url}")
        # Usar domcontentloaded (más rápido) y confiar en wait_for_selector
        await page.goto(url, timeout=90000, wait_until="domcontentloaded")

        # --- ESPERA ROBUSTA (¡Importante!) ---
        try:
            # ¡¡VERIFICA Y AJUSTA ESTE SELECTOR!! Ej: "#hp_hotel_name"
            selector_estable = "#hp_hotel_name"
            print(f"Esperando selector estable: '{selector_estable}'")
            await page.wait_for_selector(selector_estable, state="visible", timeout=30000)
            print("Selector estable encontrado.")
        except PlaywrightTimeoutError:
            print(f"Advertencia: No se encontró el selector estable '{selector_estable}' en 30s para {url}. Puede que falten datos.")

        # --- Obtener HTML ---
        print("Intentando obtener page.content()...")
        html = await page.content()
        print(f"HTML obtenido para {url} (Tamaño: {len(html)} bytes)")

        if not html:
            print(f"Advertencia: El contenido HTML está vacío para {url}.")
            return {"error": "HTML vacío", "url_original": url, "details": "No se pudo obtener contenido HTML."}, ""

        # --- Parseo ---
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url) # Llama a la función de parseo limpia

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
        # Solo cerrar la página, el navegador lo cierra el llamador (procesar_urls_en_lote)
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
                            data_extraida = item; break
                    if data_extraida: break
                except json.JSONDecodeError: continue
    except Exception as e: print(f"Error extrayendo JSON-LD: {e}")

    # Extraer Imágenes
    try:
        scripts_json = soup.find_all('script', type='application/json')
        for script in scripts_json:
            if script.string and ('large_url' in script.string or '"url_max300"' in script.string):
                try:
                    data_json = json.loads(script.string)
                    stack = [data_json]; found_urls = set()
                    while stack and len(imagenes_secundarias) < 15: # Límite aumentado
                        current = stack.pop()
                        if isinstance(current, dict):
                            for key, value in current.items():
                                if key in ('large_url', 'url_max1280', 'url_original') and isinstance(value, str) and value.startswith('https://') and '.staticflickr.com' not in value:
                                    if value not in found_urls:
                                        imagenes_secundarias.append(value); found_urls.add(value)
                                elif isinstance(value, (dict, list)): stack.append(value)
                        elif isinstance(current, list): stack.extend(reversed(current))
                except json.JSONDecodeError: continue
    except Exception as e: print(f"Error extrayendo imágenes de JSON: {e}")

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
    except Exception as e: print(f"Error extrayendo servicios: {e}")

    # Extraer Títulos H1 y H2
    titulo_h1 = soup.find("h1").get_text(strip=True) if soup.find("h1") else data_extraida.get("name", "")
    bloques_contenido_h2 = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]

    # Construir el diccionario final (SIN IPs)
    address_info = data_extraida.get("address", {})
    rating_info = data_extraida.get("aggregateRating", {})

    return {
        # Metadatos
        "url_original": url,
        "fecha_scraping": datetime.datetime.now(datetime.timezone.
