import streamlit as st
import requests
from bs4 import BeautifulSoup

def render_scraping_booking():
    st.header("🌐 Scraping directo de Booking con BeautifulSoup")

    query = st.text_input("📍 Ciudad destino", "Tenerife")
    url = f"https://www.booking.com/searchresults.es.html?ss={query.replace(' ', '+')}"

    if st.button("🔍 Buscar hoteles"):
        st.write(f"🔗 URL usada: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/117.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")

            hoteles = soup.select("div[data-testid='property-card']")
            st.success(f"✅ Se encontraron {len(hoteles)} hoteles")

            for hotel in hoteles[:10]:
                nombre = hotel.select_one("div[data-testid='title']")
                if nombre:
                    st.markdown(f"### 🏨 {nombre.get_text(strip=True)}")
        except Exception as e:
            st.error(f"❌ Error al obtener resultados: {e}")
