# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup


def render_scraping_booking():
    st.header("📦 Scraping de Hoteles en Booking (BeautifulSoup)")

    st.markdown("### ✍️ Parámetros de búsqueda")
    location = st.text_input("📍 Ciudad destino", "Tenerife")

    if st.button("📥 Obtener datos de los hoteles"):
        url = f"https://www.booking.com/searchresults.es.html?ss={location.replace(' ', '+')}"
        st.write(f"🔗 URL utilizada: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/117.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            hoteles = soup.find_all("div", attrs={"data-testid": "property-card"})

            if not hoteles:
                st.warning("⚠️ No se encontraron resultados con 'property-card'.")
                return

            st.success(f"✅ Se encontraron {len(hoteles)} hoteles")
            st.subheader("🏨 Hoteles encontrados:")

            for hotel in hoteles[:10]:
                h3 = hotel.find("h3")
                nombre = h3.get_text(strip=True) if h2 else "Nombre no disponible"
                st.markdown(f"### 🏨 {nombre}")
        except Exception as e:
            st.error(f"❌ Error durante el scraping: {e}")
