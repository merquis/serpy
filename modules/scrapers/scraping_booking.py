# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup

def render_scraping_booking():
    st.header("Scraping Booking estilo BrightData adaptado")

    url = st.text_input("🔗 URL de la página de Booking (ej. listado)", "https://www.booking.com/searchresults.es.html?ss=mallorca")
    enviar = st.button("🔍 Scrappear hoteles")

    if enviar:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/117.0.0.0 Safari/537.36'
        }

        try:
            page = requests.get(url, headers=headers)
            page.raise_for_status()
        except Exception as e:
            st.error(f"❌ Error al cargar la página: {e}")
            return

        soup = BeautifulSoup(page.text, 'html.parser')

        st.subheader("🏨 Hoteles encontrados:")

        # Adaptación básica para Booking: título de hotel en resultado de búsqueda
        hoteles = soup.find_all('div', class_='fcab3ed991 a23c043802')  # título visible

        if not hoteles:
            st.warning("⚠️ No se encontraron títulos de hotel con la clase esperada.")

        for h in hoteles:
            nombre = h.get_text(strip=True)
            st.markdown(f"### 🏨 {nombre}")
            st.markdown("---")
