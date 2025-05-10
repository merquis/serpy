# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

# ════════════════════════════════════════════════
# 📡 Configuración del proxy Bright Data
# ════════════════════════════════════════════════
proxy_url = "http://brd-customer-hl_bdec3e3e-zone-scraping_hoteles-country-es:9kr59typny7y@brd.superproxy.io:33335"

def obtener_datos_booking(urls):
    """
    Función que recibe una lista de URLs de hoteles de Booking y devuelve sus nombres extraídos.
    """
    resultados_json = []

    for url in urls:
        # Configurar proxy y cabeceras HTTP
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        }

        try:
            # Solicitud GET a la URL usando el proxy
            response = requests.get(url, headers=headers, proxies=proxies, verify=False, timeout=30)

            # Validar respuesta
            if response.status_code != 200:
                st.error(f"❌ Error {response.status_code} para URL {url}")
                continue

            # Parsear el HTML recibido
            soup = BeautifulSoup(response.text, "html.parser")

            # Buscar el nombre del hotel
            nombre_hotel = soup.select_one('[data-testid="title"]')
            if not nombre_hotel:
                nombre_hotel = soup.select_one('h2.pp-header__title')

            # Obtener nombre limpio
            if nombre_hotel:
                nombre_final = nombre_hotel.text.strip()
            else:
                nombre_final = None

            # Guardar resultados
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
    st.title("🏨 Scraping de nombres de hoteles en Booking")

    # Inicializar entradas si no existen
    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    # UI para introducir URLs
    col1, _ = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear nombres")

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    # Cuando se pulsa el botón
    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Scrapeando nombres de hoteles..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados

    # Mostrar resultados si existen
    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)
