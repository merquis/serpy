# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

# 👉 Proxy residencial de Bright Data
proxy_url = "http://brd-customer-hl_bdec3e3e-zone-scraping_hoteles-country-es:9kr59typny7y@brd.superproxy.io:33335"

def obtener_datos_booking(urls):
    resultados_json = []

    for url in urls:
        st.write(f"📡 Scrapeando URL: {url}")

        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers, proxies=proxies, verify=False, timeout=30)
            st.write(f"🔎 Código de respuesta HTTP: {response.status_code}")

            if response.status_code != 200:
                st.error(f"❌ Error {response.status_code} para URL {url}")
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

            # Buscar el nombre del hotel
            nombre_hotel = soup.select_one('[data-testid="title"]')
            if not nombre_hotel:
                nombre_hotel = soup.select_one('h2.pp-header__title')

            if nombre_hotel:
                nombre_final = nombre_hotel.text.strip()
                st.success(f"🏨 Nombre hotel encontrado: {nombre_final}")
            else:
                nombre_final = None
                st.warning(f"⚠️ No se pudo encontrar el nombre del hotel.")

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
        with st.spinner("🔄 Consultando a través de proxy Bright Data..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados
        # ⛔️ IMPORTANTE: NO recargamos automáticamente, para ver todos los mensajes

    if st.session_state.resultados_json:
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.resultados_json)
