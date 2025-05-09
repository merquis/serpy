# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup


def render_scraping_booking():
    st.header("Scraping Booking")
    st.markdown("Extraer nombre del hotel desde una URL de Booking")

    url = st.text_input("URL del hotel en Booking", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")

    if st.button("🔍 Obtener nombre del hotel"):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            # Booking usa <h2 id="hp_hotel_name"> o variantes
            titulo = soup.find("h2", id="hp_hotel_name")
            if not titulo:
                titulo = soup.find("h1")

            if titulo:
                nombre = titulo.get_text(strip=True)
                st.success(f"🏨 Nombre detectado: {nombre}")
            else:
                st.warning("No se pudo encontrar el nombre del hotel en la página.")

        except Exception as e:
            st.error(f"❌ Error al hacer scraping: {e}")
