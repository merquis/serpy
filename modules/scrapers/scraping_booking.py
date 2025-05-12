import streamlit as st
import asyncio
import ssl
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
def get_proxy_settings():
    try:
        proxy_config = st.secrets["brightdata_booking"]
        proxy_server = proxy_config.get("host")
        proxy_port = proxy_config.get("port")
        proxy_username = proxy_config.get("username")
        proxy_password = proxy_config.get("password")

        if proxy_server and proxy_port and proxy_username and proxy_password:
            return {
                "server": proxy_server,
                "port": int(proxy_port),
                "username": proxy_username,
                "password": proxy_password
            }
        else:
            return None
    except Exception as e:
        st.error(f"❌ Error leyendo configuración proxy: {e}")
        return None

# ════════════════════════════════════════════════════
# 🌐 Detectar IP real (sin proxy)
# ════════════════════════════════════════════════════
def detectar_ip_real():
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        if response.status_code == 200:
            ip_real = response.json().get("ip", "desconocida")
            print(f"🌐 IP Real (sin proxy): {ip_real}")
            st.session_state["ip_real"] = ip_real
        else:
            st.session_state["ip_real"] = "error"
    except Exception as e:
        st.session_state["ip_real"] = "error"

# ════════════════════════════════════════════════════
# 🔎 Verificar IP pública con proxy (usando Playwright)
# ════════════════════════════════════════════════════
async def verificar_ip(page):
    try:
        await page.goto("https://api.ipify.org?format=json", timeout=10000)
        ip_info = await page.text_content("body")
        ip_json = json.loads(ip_info)
        ip_actual = ip_json.get("ip", "desconocida")
        st.session_state["last_detected_ip"] = ip_actual
    except Exception as e:
        st.session_state["last_detected_ip"] = "error"

# ════════════════════════════════════════════════════
# 📅 Scraping Booking usando Playwright + Proxy + SSL
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance=None, debug=False):
    html = ""
    close_browser_on_finish = False
    current_p = None

    try:
        if not browser_instance:
            close_browser_on_finish = True
            current_p = await async_playwright().start()
            proxy_conf = get_proxy_settings()
            if not proxy_conf:
                raise Exception("Proxy no configurado")

            proxy_address = f"http://{proxy_conf['username']}:{proxy_conf['password']}@{proxy_conf['server']}:{proxy_conf['port']}"

            browser_instance = await current_p.chromium.launch(
                headless=True,
                proxy={"server": proxy_address},
                args=["--ignore-certificate-errors"]
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
            pass

        html = await page.content()
        await page.close()

    except PlaywrightTimeoutError as e:
        return {"error": "Timeout de Playwright", "url": url, "details": str(e)}, ""
    except Exception as e:
        return {"error": "Error Playwright/red", "url": url, "details": str(e)}, ""
    finally:
        if close_browser_on_finish and browser_instance:
            await browser_instance.close()
        if close_browser_on_finish and current_p:
            await current_p.stop()

    if not html:
        return {"error": "HTML vacío", "url": url}, ""

    soup = BeautifulSoup(html, "html.parser")
    resultado = parse_html_booking(soup, url)
    return resultado, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking
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
                    if isinstance(data_json, list):
                        for item in data_json:
                            if item.get("@type") == "Hotel":
                                data_extraida = item
                                break
                    elif isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                        data_extraida = data_json
                        break
                except Exception:
                    continue
    except Exception as e:
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
                            if k == 'large_url' and isinstance(v, str):
                                if v not in imagenes_secundarias:
                                    imagenes_secundarias.append(v)
                            elif isinstance(v, (dict, list)):
                                stack.append(v)
                    elif isinstance(current, list):
                        stack.extend(current)
    except Exception:
        pass

    try:
        svc_elements = soup.find_all('div', class_="bui-list__description")
        for svc in svc_elements:
            texto = svc.get_text(strip=True)
            if texto and texto not in servicios:
                servicios.append(texto)
    except Exception:
        pass

    return {
        "ip_real": st.session_state.get("ip_real", "desconocida"),
        "ip_con_proxy": st.session_state.get("last_detected_ip", "desconocida"),
        "url_original": url,
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
# 🗂️ Procesar varias URLs en lote
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar):
    tasks_results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        tasks = [obtener_datos_booking_playwright(u, browser) for u in urls_a_procesar]
        results = await asyncio.gather(*tasks)

        for r, html_content in results:
            tasks_results.append(r)
            if not r.get("error"):
                st.session_state.last_successful_html_content = html_content

        await browser.close()

    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.session_state.setdefault("_called_script", "scraping_booking")
    st.title("🏨 Scraping hoteles Booking")

    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_json", [])
    st.session_state.setdefault("last_successful_html_content", "")

    st.session_state.urls_input = st.text_area("📝 URLs de hoteles:", st.session_state.urls_input, height=150)

    col1, col2, col3 = st.columns(3)

    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles")

    if buscar_btn:
        detectar_ip_real()
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        if urls:
            with st.spinner(f"Scrapeando {len(urls)} hoteles..."):
                resultados = asyncio.run(procesar_urls_en_lote(urls))
                st.session_state.resultados_json = resultados
            st.rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)

    if st.session_state.last_successful_html_content:
        st.subheader("📄 Último HTML capturado")
        st.download_button(
            label="⬇️ Descargar HTML",
            data=st.session_state.last_successful_html_content.encode("utf-8"),
            file_name="hotel_booking.html",
            mime="text/html"
        )
