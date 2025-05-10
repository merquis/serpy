# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from modules.utils.drive_utils import subir_json_a_drive  # Seguimos pudiendo exportar o subir JSON

def obtener_datos_booking(urls):
    """
    Función de prueba SIN usar headers ni proxies
    """
    resultados_json = []

    for url in urls:
        try:
            # 🚨 ATENCIÓN: Petición directa sin headers ni proxy
            response = requests.get(url, verify=False, timeout=30)

            if response.status_code != 200:
                st.error(f"❌ Error {response.status_code} para URL {url}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # Buscar el nombre del hotel
            nombre_hotel = soup.select_one('[data-testid="title"]')
            if not nombre_hotel:
                nombre_hotel = soup.select_one('h2.pp-header__title')

            if nombre_hotel:
                nombre_final = nombre_hotel.text.strip()
            else:
                nombre_final = None

            resultados_json.append({
                "url": url,
                "nombre_hotel": nombre_final
            })

        except Exception as e:
            st.error(f"❌ Error inesperado procesando {url}: {e}")

    return resultados_json

def render_scraping_booking():
    """
    Interfaz Streamlit para el scraping de Booking.com
    """
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping de nombres de hoteles en Booking (PRUEBA SIN HEADERS NI PROXY)")

    # Inicializar inputs si no existen
    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    # UI para introducir URLs
    col1, _ = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear nombre hotel (modo prueba)")

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    # Al pulsar el botón
    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Scrapeando nombres de hoteles..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados

    # Mostrar resultados
    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)

        # Descargar JSON
        nombre_archivo = "datos_hoteles_booking.json"
        json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.download_button(
                "⬇️ Exportar JSON",
                data=json_bytes,
                file_name=nombre_archivo,
                mime="application/json"
            )

        # Subir JSON a Google Drive
        with col2:
            if st.button("☁️ Subir a Google Drive") and st.session_state.get("proyecto_id"):
                enlace = subir_json_a_drive(nombre_archivo, json_bytes, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Subido correctamente: [Ver archivo]({enlace})", icon="📁")
