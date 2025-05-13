import streamlit as st
import asyncio
import json
import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# ════════════════════════════════════════════════════
# 🛠️ Recursos a bloquear (sin afectar Booking/Bstatic)
# ════════════════════════════════════════════════════
DOMINIOS_A_BLOQUEAR = [
    "googletagmanager.com", "cdn.cookielaw.org", "onetrust.com", "cookielaw.org",
    "tags.tiqcdn.com", "usercentrics.com", "app.usercentrics.eu",
    "google-analytics.com", "analytics.google.com", "omtrdc.net",
    "dpm.demdex.net", "scorecardresearch.com", "sb.scorecardresearch.com",
    "nr-data.net", "googletagservices.com", "googlesyndication.com",
    "doubleclick.net", "adservice.google.com", "connect.facebook.net",
    "staticxx.facebook.com", "www.facebook.com/tr/", "criteo.com",
    "criteo.net", "static.criteo.net", "targeting.criteo.com",
    "adnxs.com", "rubiconproject.com", "casalemedia.com",
    "pubmatic.com", "amazon-adsystem.com", "adsystem.amazon.com",
    "aax.amazon-adsystem.com", "bing.com/ads", "bat.bing.com",
    "ads.microsoft.com", "yieldlab.net", "creativecdn.com",
    "optimizely.com", "adobedtm.com", "assets.adobedtm.com",
    "everesttech.net", "krxd.net", "rlcdn.com",
]

PATRONES_URL_A_BLOQUEAR = [
    "/tracking", "/analytics", "/ads", "/advert", "/banner",
    "beacon", "pixel", "collect", "gtm.js", "analytics.js",
    "sdk.js", "OtAutoBlock.js", "otSDKStub.js", "otBannerSdk.js",
    "challenge.js", "optanon",
]

def should_block_resource(request):
    """Bloquea solo recursos externos, nunca Booking ni Bstatic."""
    res_type = request.resource_type
    res_url = request.url.lower()

    if "booking.com" in res_url or "bstatic.com" in res_url:
        return False

    if res_type in ["script", "xhr", "fetch"]:
        for domain in DOMINIOS_A_BLOQUEAR:
            if domain in res_url:
                return True
        for pattern in PATRONES_URL_A_BLOQUEAR:
            if pattern in res_url:
                return True

    return False

# ════════════════════════════════════════════════════
# 📅 Scraping Booking usando Playwright
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright_simple(url: str, browser_instance):
    html = ""
    resultado_final = {}
    context = None
    page = None

    try:
        context = await browser_instance.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        await page.route("**/*", lambda route: route.abort() if should_block_resource(route.request) else route.continue_())

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
        "metodo_extraccion": "Playwright_Simple_Bloqueado",
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
# 🗂️ Procesar URLs en lote
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote_simple(urls_a_procesar):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        tasks = [obtener_datos_booking_playwright_simple(url, browser) for url in urls_a_procesar]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        await browser.close()

    final_results = []
    for i, res in enumerate(results):
        url_p = urls_a_procesar[i]
        if isinstance(res, Exception):
            final_results.append({"error": "Fallo_Excepcion_Gather", "url_original": url_p, "details": str(res)})
        elif isinstance(res, tuple) and len(res) == 2:
            res_dict, html_content = res
            final_results.append(res_dict)
            if not res_dict.get("error") and html_content:
                st.session_state.last_successful_html_content = html_content
        else:
            final_results.append({"error": "Fallo_ResultadoInesperado", "url_original": url_p, "details": str(res)})

    return final_results

# ════════════════════════════════════════════════════
# 🎯 Interfaz Streamlit
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.title("🏨 Scraping Hoteles Booking (Playwright Mejorado)")
    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales", [])
    st.session_state.setdefault("last_successful_html_content", "")

    st.session_state.urls_input = st.text_area(
        "📝 Pega URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150
    )

    if st.button("🔍 Scrapear Hoteles"):
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.startswith("https://www.booking.com/hotel/")]

        if not urls:
            st.warning("Introduce URLs válidas de Booking.com.")
            st.stop()

        with st.spinner(f"Procesando {len(urls)} URLs..."):
            resultados = asyncio.run(procesar_urls_en_lote_simple(urls))
        st.session_state.resultados_finales = resultados
        st.rerun()

    if st.session_state.resultados_finales:
        st.subheader("📊 Resultados")
        st.json(st.session_state.resultados_finales)

    if st.session_state.last_successful_html_content:
        st.subheader("📄 Último HTML Capturado")
        html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
        st.download_button("⬇️ Descargar HTML", data=html_bytes, file_name="hotel_booking.html", mime="text/html")

# ════════════════════════════════════════════════════
# 🚀 Ejecutar App
# ════════════════════════════════════════════════════
if __name__ == "__main__":
    render_scraping_booking()
