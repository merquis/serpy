# modules/scrapers/scraping_booking.py

import streamlit as st
import json
import ssl
import urllib.error
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ══════════════════════════════════════════════════
# 📡 Configuración del proxy Bright Data
# ══════════════════════════════════════════════════
proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-scraping_hoteles-country-es:9kr59typny7y@brd.superproxy.io:33335'

# ══════════════════════════════════════════════════
# 📅 Funciones
# ══════════════════════════════════════════════════

def obtener_datos_booking(urls):
    resultados = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy={"server": proxy_url})
            context = browser.new_context()
            page = context.new_page()

            for url in urls:
                try:
                    page.goto(url, timeout=60000)
                    page.wait_for_load_state('networkidle')

                    nombre_hotel = page.locator('[data-testid="title"]').first
                    if not nombre_hotel.count():
                        nombre_hotel = page.locator('h2.pp-header__title').first

                    valoracion = page.locator('[data-testid="review-score"]').first
                    direccion = page.locator('[data-testid="address"]').first
                    if not direccion.count():
                        direccion = page.locator('span.hp_address_subtitle').first

                    precio_minimo = page.locator('[data-testid="price-and-discounted-price"]').first

                    resultados.append({
                        "nombre_hotel": nombre_hotel.inner_text().strip() if nombre_hotel.count() else None,
                        "aid": "linkafiliado",
                        "checkin": "2025-05-11",  # Opcional: Puedes incluir fecha si quieres guardar la fecha de scraping
                        "checkout": "2025-05-12",
                        "group_adults": "2",
                        "group_children": "0",
                        "no_rooms": "1",
                        "dest_id": "-369166",
                        "dest_type": "city",
                        "valoracion": valoracion.inner_text().strip() if valoracion.count() else None,
                        "numero_opiniones": None,
                        "direccion": direccion.inner_text().strip() if direccion.count() else None,
                        "precio_minimo": precio_minimo.inner_text().strip() if precio_minimo.count() else None,
                        "url": url
                    })

                except Exception as e:
                    st.error(f"❌ Error procesando {url}: {e}")

            browser.close()

    except Exception as e:
        st.error(f"❌ Error inicializando navegador Playwright: {e}")

    return resultados


def subir_resultado_a_drive(nombre_archivo, contenido_bytes):
    proyecto_id = st.session_state.get("proyecto_id")
    if not proyecto_id:
        st.error("❌ No hay proyecto seleccionado en session_state['proyecto_id'].")
        return

    subcarpeta_id = obtener_o_crear_subcarpeta("scraper url hotel booking", proyecto_id)
    if not subcarpeta_id:
        st.error("❌ No se pudo encontrar o crear la subcarpeta.")
        return

    enlace = subir_json_a_drive(nombre_archivo, contenido_bytes, subcarpeta_id)
    if enlace:
        st.success(f"✅ Subido correctamente: [Ver archivo]({enlace})", icon="📁")
    else:
        st.error("❌ Error al subir el archivo a la subcarpeta.")


def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    hoy = datetime.today()
    manana = hoy + timedelta(days=1)

    fecha_checkin = hoy.strftime('%Y-%m-%d')
    fecha_checkout = manana.strftime('%Y-%m-%d')

    url_demo = f"https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?aid=linkafiliado&checkin={fecha_checkin}&checkout={fecha_checkout}&group_adults=2&group_children=0&no_rooms=1&dest_id=-369166&dest_type=city"

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = url_demo

    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear nombre hotel", key="buscar_nombre_hotel")

    if st.session_state.resultados_json:
        nombre_archivo = "datos_hoteles_booking.json"
        contenido_json = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

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
                with st.spinner("☁️ Subiendo JSON a Google Drive (cuenta de servicio)..."):
                    subir_resultado_a_drive(nombre_archivo, contenido_json)

    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Scrapeando nombres de hoteles..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)
