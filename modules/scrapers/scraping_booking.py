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
        st.markdown("### 🔍 HTML recibido (vista previa)")
        st.code(page.text[:1500])

        st.subheader("🏨 Hoteles encontrados:")

        # Adaptación básica para Booking: título de hotel en resultado de búsqueda
        cards = soup.select('div[data-testid="property-card"]')

        if not cards:
            st.warning("⚠️ No se encontraron resultados con 'property-card'.")

        for card in cards[:10]:
            nombre = card.select_one('div[data-testid="title"]')
            enlace = card.find('a', href=True)
            location_element = card.find('span', {'data-testid': 'address'})
            price_element = card.find('span', {'data-testid': 'price-and-discounted-price'})
            rating_element = card.find('div', {'class': 'b5cd09854e d10a6220b4'})

            if nombre and enlace:
                nombre_hotel = nombre.get_text(strip=True)
                url_hotel = "https://www.booking.com" + enlace['href'].split('?')[0]
                st.markdown(f"### 🏨 [{nombre_hotel}]({url_hotel})")
                st.markdown(f"`{url_hotel}`")
                if location_element:
                    st.write(f"📍 {location_element.text.strip()}")
                if price_element:
                    st.write(f"💰 {price_element.text.strip()}")
                if rating_element:
                    st.write(f"⭐ {rating_element.text.strip()}")
                st.markdown("---")
