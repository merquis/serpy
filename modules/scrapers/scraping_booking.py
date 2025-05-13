import streamlit as st
import asyncio
import json
import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# ════════════════════════════════════════════════════
# 🛠️ Utilidades
# ════════════════════════════════════════════════════
def validar_url_booking(url: str) -> bool:
    """Valida que sea una URL de Booking válida para scraping."""
    return url.startswith("https://www.booking.com/hotel/") and url.endswith(".html")

# ════════════════════════════════════════════════════
# 📅 Scraping Booking con Playwright (Versión PRO Mejorada)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright_simple(url: str, browser_instance):
    """Obtiene datos de una URL de Booking usando Playwright."""
    html = ""
    resultado_final = {}
    page = None

    try:
        context = await browser_instance.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        retries = 2
        for intento in range(retries):
            try:
                await page.goto(url, timeout=60000, wait_until="networkidle")
                await page.wait_for_selector("#hp_hotel_name, h1", timeout=15000)
                break
            except PlaywrightTimeoutError as e:
                print(f"Intento {intento+1} fallido en {url}: {e}")
                if intento == retries - 1:
                    raise

        html = await page.content()
        if not html:
            return {"error": "Fallo_HTML_Vacio_Playwright", "url_original": url, "details": "No se obtuvo contenido HTML."}, ""

        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url)

    except Exception as e:
        error_type = type(e).__name__
        details = str(e)
        return {"error": f"Fallo_Excepcion_Playwright_{error_type}", "url_original": url, "details": details}, ""
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass
        if context:
            try:
                await context.close()
            except Exception:
                pass

    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
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
                    data_json = json.loads(script.string)
                    if isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                        data_extraida = data_json
                        break
                except:
                    continue
    except:
        pass

    try:
        found_urls_img = set()
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if src and src.startswith("https://cf.bstatic.com") and src not in found_urls_img and len(imagenes_secundarias) < 15:
                imagenes_secundarias.append(src)
                found_urls_img.add(src)
    except:
        pass

    try:
        possible_classes = ["hotel-facilities__list", "facilitiesChecklistSection", "hp_desc_important_facilities", "bui-list__description", "db29ecfbe2"]
        servicios_set = set()
        for cn in possible_classes:
            for container in soup.find_all(class_=cn):
                for item in container.find_all(['li', 'span', 'div'], recursive=True):
                    texto = item.get_text(strip=True)
                    if texto and len(texto) > 3:
                        servicios_set.add(texto)
        servicios = sorted(list(servicios_set))
    except:
        pass

    titulo_h1_tag = soup.find("h1")
    titulo_h1 = titulo_h1_tag.get_text(strip=True) if titulo_h1_tag else data_extraida.get("name", "")
    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]

    address_info = data_extraida.get("address", {})
    rating_info = data_extraida.get("aggregateRating", {})

    return {
        "url_original": url,
        "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "metodo_extraccion": "Playwright_Simple_Optimizado",
        "busqueda_checkin": checkin_year_month_day,
        "busqueda_checkout": checkout_year_month_day,
        "busqueda_adultos": group_adults,
        "busqueda_ninos": group_children,
        "busqueda_habitaciones": no_rooms,
        "busqueda_tipo_destino": dest_type,
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
        "titulo_h1": titulo_h1,
        "subtitulos_h2": h2s,
        "servicios_principales": servicios,
        "imagenes": imagenes_secundarias,
    }

# ════════════════════════════════════════════════════
# 🗂️ Procesar Lote
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote_simple(urls_a_procesar):
    tasks_results = []
    browser_launch_options = {"headless": True}

    async with async_playwright() as p:
        browser = await p.chromium.launch(**browser_launch_options)

        tasks = [obtener_datos_booking_playwright_simple(url, browser) for url in urls_a_procesar]
        results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res_or_exc in enumerate(results_with_exceptions):
            url_p = urls_a_procesar[i]
            if isinstance(res_or_exc, Exception):
                tasks_results.append({"error": "Fallo_Excepcion_Gather_Playwright_Simple", "url_original": url_p, "details": str(res_or_exc)})
            elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                res_dict, html_content = res_or_exc
                tasks_results.append(res_dict)
                if not res_dict.get("error") and html_content:
                    st.session_state.last_successful_html_content = html_content
            else:
                tasks_results.append({"error": "Fallo_ResultadoInesperado_HTTPX", "url_original": url_p, "details": str(res_or_exc)})

        await browser.close()

    return tasks_results

# ════════════════════════════════════════════════════
# 🎯 Interfaz Streamlit
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.session_state.setdefault("_called_script", "scraping_booking_playwright_simple_refactor")
    st.title("🏨 Scraping Hoteles Booking (Playwright Simple Mejorado)")
    st.caption("Modo optimizado: Usa Playwright, con contexto separado y retry inteligente.")

    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales_simple", [])
    st.session_state.setdefault("last_successful_html_content", "")

    st.session_state.urls_input = st.text_area(
        "📝 Pega URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150
    )

    if st.button("🔍 Scrapear Hoteles"):
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if validar_url_booking(url)]
        if not urls:
            st.warning("Introduce URLs válidas de Booking.com.")
            st.stop()

        with st.spinner(f"Procesando {len(urls)} URLs..."):
            resultados_actuales = asyncio.run(procesar_urls_en_lote_simple(urls))

        st.session_state.resultados_finales_simple = resultados_actuales
        st.rerun()

    if st.session_state.resultados_finales_simple:
        st.subheader("📊 Resultados")
        st.json(st.session_state.resultados_finales_simple)

    if st.session_state.last_successful_html_content:
        st.subheader("📄 Último HTML Capturado")
        html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
        st.download_button(label="⬇️ Descargar HTML", data=html_bytes, file_name="hotel_booking.html", mime="text/html")

# ════════════════════════════════════════════════════
# 🚀 Lanzador
# ════════════════════════════════════════════════════
if __name__ == "__main__":
    render_scraping_booking()
