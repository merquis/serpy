# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup

def render_scraping_booking():
    st.header("Scraping Booking con BeautifulSoup")

    url_input = st.text_input("🔗 URL del hotel en Booking", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    enviar = st.button("🔍 Obtener nombre del hotel")

    if enviar:
        st.info("⏳ Realizando solicitud HTTP...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(url_input, headers=headers)
            response.raise_for_status()
        except requests.RequestException as e:
            st.error(f"❌ Error en la solicitud HTTP: {e}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        h2 = soup.find("h2")

        if h2:
            st.success(f"🏨 Nombre del hotel: {h2.get_text(strip=True)}")
        else:
            st.warning("⚠️ No se pudo encontrar el título del hotel en la página.")
