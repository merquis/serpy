# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import json
import datetime
from urllib.parse import urlparse, parse_qs
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

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
# 🔎 Verificar IP pública
# ════════════════════════════════════════════════════

async def verificar_ip(page):
    try:
        await page.goto("https://api.ipify.org?format=json", timeout=10000)
        ip_info = await page.text_content("body")
        ip_json = json.loads(ip_info)
        ip_actual = ip_json.get("ip", "desconocida")
        print(f"🌐 IP pública detectada: {ip_actual}")
        st.session_state["last_detected_ip"] = ip_actual
    except Exception as e:
        print(f"⚠️ Error verificando IP: {e}")
        st.session_state["last_detected_ip"] = "error"

# ════════════════════════════════════════════════════
# 📅 Función principal de scraping Booking
# ════════════════════════════════════════════════════

async def obtener_datos_booking_playwright(url: str, browser_instance=None, debug=False):
    html = ""
    close_browser_on_finish = False
    current_p = None

    try:
        if not browser_instance:
            close_browser_on_finish = True
            current_p = await async_playwright().start()
            proxy_config = get_proxy_settings()
            browser_instance = await current_p.chromium.launch(
                headless=True,
                proxy=proxy_config
            )

        page = await browser_instance.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        if debug:
            await verificar_ip(page)

        await page.goto(url, timeout=90000, wait_until="domcontentloaded")

        try:
            await page.wait_for_selector('script[type="application/ld+json"]', timeout=20000)
        except PlaywrightTimeoutError:
            print(f"⚠️ Timeout esperando JSON-LD en {url}. Seguimos con lo que tengamos.")

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

    # Procesar el HTML
    soup = BeautifulSoup(html, "html.parser")

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    group_adults = query_params.get('group_adults', ['2'])[0]
    group_children = query_params.get('group_children', ['0'])[0]
    no_rooms = query_params.get('no_rooms', ['1'])[0]
    dest_type = query_params.get('dest_type', ['city'])[0]

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
                    if isinstance(data_json, list):
                        for item in data_json:
                            if item.get("@type") == "Hotel":
                                data_extraida = item
                                break
                        if data_extraida:
                            break
                    elif isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                        data_extraida = data_json
                        break
                except Exception as e:
                    print(f"Error parseando JSON-LD: {e}")
    except Exception as e:
        print(f"Error buscando scripts JSON-LD: {e}")

    # Extraer imágenes
    try:
        scripts_json = soup.find_all('script', type='application/json')
        for script in scripts_json:
            if script.string and 'large_url' in script.string:
                try:
                    data_json = json.loads(script.string)
                    stack = [data_json]
                    while stack and len(imagenes_secundarias) < 10:
                        current = stack.pop()
                        if isinstance(current, dict):
                            for k, v in current.items():
                                if k == 'large_url' and isinstance(v, str) and v.startswith("https://cf.bstatic.com/xdata/images/hotel/max1024x768/"):
                                    if v not in imagenes_secundarias:
                                        imagenes_secundarias.append(v)
                                else:
                                    if isinstance(v, (dict, list)):
                                        stack.append(v)
                        elif isinstance(current, list):
                            stack.extend(current)
                except Exception as e:
                    print(f"Error parseando JSON de imágenes: {e}")
    except Exception as e:
        print(f"Error buscando imágenes JSON: {e}")

    # Extraer servicios
    try:
        svc_elements = soup.find_all('div', class_="bui-list__description")
        for svc in svc_elements:
            texto = svc.get_text(strip=True)
            if texto and texto not in servicios:
                servicios.append(texto)
    except Exception as e:
        print(f"Error extrayendo servicios: {e}")

    resultado = {
        "url_original": url,
        "checkin": datetime.date.today().strftime("%Y-%m-%d"),
        "checkout": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "group_adults": group_adults,
        "group_children": group_children,
        "no_rooms": no_rooms,
        "dest_type": dest_type,
        "nombre_alojamiento": data_extraida.get("name"),
        "direccion": data_extraida.get("address", {}).get("streetAddress"),
        "tipo_alojamiento": data_extraida.get("@type"),
        "slogan_principal": None,
        "descripcion_corta": data_extraida.get("description"),
        "estrellas": None,
        "precio_noche": None,
        "alojamiento_destacado": None,
        "isla_relacionada": None,
        "frases_destacadas": [],
        "servicios": servicios,
        "valoracion_limpieza": None,
        "valoracion_confort": None,
        "valoracion_ubicacion": None,
        "valoracion_instalaciones_servicios": None,
        "valoracion_personal": None,
        "valoracion_calidad_precio": None,
        "valoracion_wifi": None,
        "valoracion_global": data_extraida.get("aggregateRating", {}).get("ratingValue"),
        "imagenes": imagenes_secundarias,
        "enlace_afiliado": url,
        "sitio_web_oficial": None,
        "titulo_h1": soup.find("h1").get_text(strip=True) if soup.find("h1") else None,
        "bloques_contenido_h2": [h2.get_text(strip=True) for h2 in soup.find_all("h2")]
    }

    return resultado, html

# (Te paso ahora mismo la parte de la interfaz de Streamlit para que completes el fichero. 🚀)
