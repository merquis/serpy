# modules/scrapers/scraping_booking.py

import streamlit as st
import json
from bs4 import BeautifulSoup
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
from playwright.sync_api import sync_playwright

# ══════════════════════════════════════════════════
# 📅 Funciones
# ══════════════════════════════════════════════════

def obtener_html_booking(url):
    """Obtiene el HTML completo usando Playwright."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)  # 60 segundos de timeout
            page.wait_for_timeout(3000)    # Espera 3 segundos para que cargue contenido dinámico
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        st.error(f"❌ Error cargando la página {url}: {e}")
        return None

def obtener_datos_booking(urls):
    """Extrae datos de hoteles de una lista de URLs."""
    resultados = []
    for url in urls:
        html = obtener_html_booking(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")

        nombre_hotel = soup.select_one('[data-testid="title"]') or soup.select_one('h2.pp-header__title')
        valoracion = soup.select_one('[data-testid="review-score"]')
        direccion = soup.select_one('[data-testid="address"]') or soup.select_one('span.hp_address_subtitle')
        precio_minimo = soup.select_one('[data-testid="price-and-discounted-price"]')

        resultados.append({
            "nombre_hotel": nombre_hotel.text.strip() if nombre_hotel else None,
            "aid": "linkafiliado",
            "checkin": "2025-05-15",
            "checkout": "2025-05-16",
            "group_adults": "2",
            "group_children": "0",
            "no_rooms": "1",
            "dest_id": "-369166",
            "dest_type": "city",
            "valoracion": valoracion.text.strip() if valoracion else None,
            "numero_opiniones": None,
            "direccion": direccion.text.strip() if direccion else None,
            "precio_minimo": precio_minimo.text.strip() if precio_minimo else None,
            "url": url
        })

    return resultados

def subir_resultado_a_drive(nombre_archivo, contenido_bytes):
    """Sube el archivo JSON al Google Drive."""
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
    """Renderiza el módulo de Scraping Booking."""
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
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
