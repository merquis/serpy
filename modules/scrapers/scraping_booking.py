# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
import json
import datetime
import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData
# ════════════════════════════════════════════════════
def get_proxy_authentication():
    try:
        proxy_conf = st.secrets["brightdata_booking"]
        host = proxy_conf["host"]
        port = proxy_conf["port"]
        username = proxy_conf["username"]
        password = proxy_conf["password"]

        proxy_server = f"http://{host}:{port}"
        credentials = {"username": username, "password": password}
        return proxy_server, credentials
    except Exception as e:
        st.error(f"❌ Error cargando configuración proxy: {e}")
        return None, None

# ════════════════════════════════════════════════════
# 🌐 Detectar IP real
# ════════════════════════════════════════════════════
def detectar_ip_real():
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        ip_real = response.json().get("ip", "desconocida")
        print(f"🌍 IP real: {ip_real}")
        st.session_state["ip_real"] = ip_real
    except Exception as e:
        print(f"⚠️ Error obteniendo IP real: {e}")
        st.session_state["ip_real"] = "error"

# ════════════════════════════════════════════════════
# 🔎 Verificar IP pública tras usar proxy
# ════════════════════════════════════════════════════
async def verificar_ip(page):
    try:
        await page.goto("https://api.ipify.org?format=json", timeout=10000)
        ip_info = await page.text_content("body")
        ip_json = json.loads(ip_info)
        ip_proxy = ip_json.get("ip", "desconocida")
        print(f"🛰️ IP pública detectada (proxy): {ip_proxy}")
        st.session_state["ip_proxy"] = ip_proxy
    except Exception as e:
        print(f"⚠️ Error verificando IP: {e}")
        st.session_state["ip_proxy"] = "error"

# ════════════════════════════════════════════════════
# 🏨 Scraping individual de hotel en Booking
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance=None, debug=False):
    html = ""
    close_browser_on_finish = False
    playwright_context = None

    try:
        if not browser_instance:
            close_browser_on_finish = True
            proxy_server, credentials = get_proxy_authentication()
            playwright_context = await async_playwright().start()
            browser_instance = await playwright_context.chromium.launch(
                headless=True,
                proxy={"server": proxy_server}
            )

        page = await browser_instance.new_page()
        proxy_server, credentials = get_proxy_authentication()
        if credentials:
            await page.authenticate(credentials)

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        if debug:
            await verificar_ip(page)

        await page.goto(url, timeout=90000, wait_until="domcontentloaded")

        try:
            await page.wait_for_selector('script[type="application/ld+json"]', timeout=20000)
        except PlaywrightTimeoutError:
            print(f"⚠️ Timeout esperando JSON-LD en {url}")

        html = await page.content()
        await page.close()

    except PlaywrightTimeoutError as e:
        return {"error": "Timeout de Playwright", "url": url, "details": str(e)}, ""
    except Exception as e:
        return {"error": "Error general Playwright", "url": url, "details": str(e)}, ""
    finally:
        if close_browser_on_finish and browser_instance:
            await browser_instance.close()
        if close_browser_on_finish and playwright_context:
            await playwright_context.stop()

    if not html:
        return {"error": "HTML vacío", "url": url}, ""

    soup = BeautifulSoup(html, "html.parser")
    resultado = parse_html_booking(soup, url)
    return resultado, html

# ════════════════════════════════════════════════════
# 🛠️ Parsear HTML de Booking
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    group_adults = query_params.get('group_adults', ['2'])[0]
    group_children = query_params.get('group_children', ['0'])[0]
    no_rooms = query_params.get('no_rooms', ['1'])[0]
    dest_type = query_params.get('dest_type', ['city'])[0]

    data_extraida = {}
    imagenes_secundarias = []
    servicios = []

    try:
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string)
                    if isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                        data_extraida = data_json
                        break
                except:
                    continue
    except:
        pass

    try:
        scripts_json = soup.find_all('script', type='application/json')
        for script in scripts_json:
            if script.string and 'large_url' in script.string:
                data_json = json.loads(script.string)
                stack = [data_json]
                while stack and len(imagenes_secundarias) < 10:
                    current = stack.pop()
                    if isinstance(current, dict):
                        for k, v in current.items():
                            if k == 'large_url' and isinstance(v, str) and 'max1024x768' in v:
                                imagenes_secundarias.append(v)
                            elif isinstance(v, (dict, list)):
                                stack.append(v)
                    elif isinstance(current, list):
                        stack.extend(current)
    except:
        pass

    try:
        svc_elements = soup.find_all('div', class_="bui-list__description")
        for svc in svc_elements:
            texto = svc.get_text(strip=True)
            if texto and texto not in servicios:
                servicios.append(texto)
    except:
        pass

    return {
        "ip_real": st.session_state.get("ip_real", "desconocida"),
        "ip_proxy": st.session_state.get("ip_proxy", "desconocida"),
        "url_original": url,
        "timestamp_scraping": datetime.datetime.now().isoformat(),
        "checkin": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "checkout": (datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        "group_adults": group_adults,
        "group_children": group_children,
        "no_rooms": no_rooms,
        "dest_type": dest_type,
        "nombre_alojamiento": data_extraida.get("name"),
        "direccion": data_extraida.get("address", {}).get("streetAddress"),
        "codigo_postal": data_extraida.get("address", {}).get("postalCode"),
        "ciudad": data_extraida.get("address", {}).get("addressLocality"),
        "pais": data_extraida.get("address", {}).get("addressCountry"),
        "tipo_alojamiento": data_extraida.get("@type"),
        "descripcion_corta": data_extraida.get("description"),
        "valoracion_global": data_extraida.get("aggregateRating", {}).get("ratingValue"),
        "numero_opiniones": data_extraida.get("aggregateRating", {}).get("reviewCount"),
        "imagenes": imagenes_secundarias,
        "servicios": servicios,
        "titulo_h1": soup.find("h1").get_text(strip=True) if soup.find("h1") else None,
        "bloques_contenido_h2": [h2.get_text(strip=True) for h2 in soup.find_all("h2")],
    }

# ════════════════════════════════════════════════════
# 🔄 Procesar scraping en lote
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar):
    resultados = []
    proxy_server, credentials = get_proxy_authentication()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy_server}
        )

        try:
            tareas = [obtener_datos_booking_playwright(u, browser) for u in urls_a_procesar]
            resultados_lote = await asyncio.gather(*tareas, return_exceptions=True)
            for r in resultados_lote:
                if isinstance(r, tuple):
                    resultados.append(r[0])
                else:
                    resultados.append({"error": "Error inesperado", "details": str(r)})
        finally:
            await browser.close()

    return resultados

# ════════════════════════════════════════════════════
# 🎯 Interfaz Streamlit Booking Scraper
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.title("🏨 Scraping Hoteles Booking (BrightData + Playwright)")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = ""
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    st.session_state.urls_input = st.text_area("🔗 URLs de Booking:", st.session_state.urls_input, height=150)

    if st.button("🔍 Iniciar Scraping"):
        urls = [u.strip() for u in st.session_state.urls_input.splitlines() if u.strip()]
        if urls:
            detectar_ip_real()
            with st.spinner("⏳ Scrapeando..."):
                resultados = asyncio.run(procesar_urls_en_lote(urls))
                st.session_state.resultados_json = resultados
            st.success("✅ Scraping completado!")
            st.rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados")
        st.json(st.session_state.resultados_json)

        nombre_archivo = f"datos_hoteles_booking_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        contenido = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        st.download_button("⬇️ Descargar JSON", contenido, file_name=nombre_archivo, mime="application/json")

        if st.button("☁️ Subir a Google Drive"):
            subir_json_a_drive(nombre_archivo, contenido)
            st.success("✅ Subido a Google Drive!")
