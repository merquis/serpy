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
def get_proxy_settings():
    try:
        proxy_server = st.secrets["brightdata_booking"]["proxy"]
        if proxy_server:
            return {"server": proxy_server}
    except Exception as e:
        st.warning(f"⚠️ No se pudo cargar el proxy: {e}")
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
            print(f"⚠️ Error obteniendo IP real: {response.status_code}")
            st.session_state["ip_real"] = "error"
    except Exception as e:
        print(f"⚠️ Error solicitando IP real: {e}")
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
        print(f"🌐 IP pública detectada (con proxy): {ip_actual}")
        st.session_state["last_detected_ip"] = ip_actual
    except Exception as e:
        print(f"⚠️ Error verificando IP pública con proxy: {e}")
        st.session_state["last_detected_ip"] = "error"

# ════════════════════════════════════════════════════
# 📅 Scraping Booking usando Playwright + Proxy
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
            print(f"⚠️ Timeout esperando JSON-LD en {url}. Continuando.")

        html = await page.content()
        await page.close()

    except PlaywrightTimeoutError as e:
        print(f"Timeout Playwright: {e}")
        return {"error": "Timeout de Playwright", "url": url, "details": str(e)}, ""
    except Exception as e:
        print(f"Error Playwright/red: {e}")
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
        print(f"Error JSON-LD: {e}")

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
                                elif isinstance(v, (dict, list)):
                                    stack.append(v)
                        elif isinstance(current, list):
                            stack.extend(current)
                except Exception as e:
                    print(f"Error imagenes: {e}")
    except Exception as e:
        print(f"Error buscando imagenes: {e}")

    try:
        svc_elements = soup.find_all('div', class_="bui-list__description")
        for svc in svc_elements:
            texto = svc.get_text(strip=True)
            if texto and texto not in servicios:
                servicios.append(texto)
    except Exception as e:
        print(f"Error extrayendo servicios: {e}")

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
    proxy_config = get_proxy_settings()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_config
        )
        try:
            tasks = [obtener_datos_booking_playwright(u, browser) for u in urls_a_procesar]
            tasks_results_with_html = await asyncio.gather(*tasks, return_exceptions=True)

            for res_or_exc in tasks_results_with_html:
                if isinstance(res_or_exc, Exception):
                    st.error(f"Error en scraping: {res_or_exc}")
                    tasks_results.append({"error": "Excepción en asyncio.gather", "details": str(res_or_exc)})
                elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                    resultado_item, html_content_item = res_or_exc
                    tasks_results.append(resultado_item)
                    if resultado_item and not resultado_item.get("error"):
                        st.session_state.last_successful_html_content = html_content_item
                else:
                    st.warning(f"Resultado inesperado: {res_or_exc}")
                    tasks_results.append({"error": "Resultado inesperado", "details": str(res_or_exc)})

        except Exception as e_browser:
            st.error(f"Error al abrir navegador: {e_browser}")
            for u_err in urls_a_procesar:
                tasks_results.append({"error": "Fallo navegador", "url": u_err, "details": str(e_browser)})
        finally:
            if browser:
                await browser.close()

    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?checkin=2025-05-12&checkout=2025-05-13&group_adults=2&group_children=0&no_rooms=1&dest_id=-369166&dest_type=city"

    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    if "last_successful_html_content" not in st.session_state:
        st.session_state.last_successful_html_content = ""

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles", key="buscar_hoteles_booking")

    if buscar_btn and st.session_state.urls_input:
        detectar_ip_real()
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        if urls:
            with st.spinner(f"🔄 Scrapeando {len(urls)} hoteles..."):
                resultados_lote = asyncio.run(procesar_urls_en_lote(urls))
                st.session_state.resultados_json = resultados_lote
            st.rerun()

    if st.session_state.resultados_json:
        nombre_archivo = f"datos_hoteles_booking_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        resultados_validos = [r for r in st.session_state.resultados_json if r and not r.get("error")]

        if resultados_validos:
            contenido_json = json.dumps(resultados_validos, ensure_ascii=False, indent=2).encode("utf-8")

            with col2:
                st.download_button(
                    label="⬇️ Exportar JSON",
                    data=contenido_json,
                    file_name=nombre_archivo,
                    mime="application/json",
                    key="descargar_json"
                )

            with col3:
                subir_a_drive_btn = st.button("☁️ Subir a Google Drive", key="subir_drive_booking")
                if subir_a_drive_btn:
                    with st.spinner("☁️ Subiendo a Drive..."):
                        subir_resultado_a_drive(nombre_archivo, contenido_json)
        else:
            with col2:
                st.info("⚠️ No hay datos válidos para exportar.")

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)

    if st.session_state.last_successful_html_content:
        st.subheader("📄 HTML capturado (última URL exitosa)")
        st.download_button(
            label="⬇️ Descargar HTML capturado",
            data=st.session_state.last_successful_html_content.encode("utf-8"),
            file_name=f"pagina_booking_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            key="descargar_html"
        )
