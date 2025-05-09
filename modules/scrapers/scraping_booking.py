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
        cards = soup.select('div[data-testid="property-card"]')

        if not cards:
            st.warning("⚠️ No se encontraron resultados con 'property-card'.")

        for card in cards:
            nombre = card.select_one('div[data-testid="title"]')
            if nombre:
                st.markdown(f"### 🏨 {nombre.get_text(strip=True)}")
                st.markdown("---")
