# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from modules.utils.drive_utils import subir_json_a_drive

def obtener_datos_booking(urls):
    token = st.secrets["brightdata"]["token"]
    api_url = "https://api.brightdata.com/request"
    resultados_json = []

    for url in urls:
        st.write(f"📡 Scrapeando URL: {url}")
        payload = {
            "zone": "serppy",
            "url": url,
            "format": "raw"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)
            st.write(f"🔎 Código de respuesta HTTP: {response.status_code}")

            if not response.ok:
                st.error(f"❌ Error {response.status_code} para URL {url}: {response.text}")
                continue

            # Mostrar pequeña parte del HTML recibido
            st.code(response.text[:500], language="html")

            soup = BeautifulSoup(response.text, "html.parser")

            if soup.title:
                st.write(f"📄 Título de la página: {soup.title.string}")
            else:
                st.warning("⚠️ No se encontró <title> en el HTML.")

            if soup.body:
                st.write("✅ El body del HTML existe.")
            else:
                st.warning("⚠️ No hay body en el HTML.")

            # 🔥 Buscar solo el nombre del hotel
            nombre_hotel = soup.select_one('[data-testid="title"]')
            if not nombre_hotel:
                nombre_hotel = soup.select_one('h2.pp-header__title')

            if nombre_hotel:
                st.success(f"🏨 Nombre hotel encontrado: {nombre_hotel.text.strip()}")
                nombre_final = nombre_hotel.text.strip()
            else:
                st.warning(f"⚠️ No se pudo encontrar el nombre del hotel.")
                nombre_final = None

            resultados_json.append({
                "url": url,
                "nombre_hotel": nombre_final
            })

        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")

    return resultados_json

def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping solo del nombre del hotel en Booking")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    col1, _ = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear nombre hotel")

    st.session_state.urls_input = st.text_area(
        "📝 Pega varias URLs de hoteles de Booking (una por línea)",
        st.session_state.urls_input,
        height=150
    )

    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Consultando BrightData para hoteles Booking..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.resultados_json)
