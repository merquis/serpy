import streamlit as st
import requests
from bs4 import BeautifulSoup

def render_scraping_booking():
    st.header("📦 Scraping de Hoteles en Booking (BeautifulSoup)")

    location = st.text_input("📍 Ciudad destino", "Tenerife")

    if st.button("📥 Obtener nombres de hoteles"):
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

            # Buscar todos los h3 visibles que parecen nombres de hotel
            hoteles = soup.find_all("h3")

            if not hoteles:
                st.warning("⚠️ No se encontraron elementos <h3> que puedan ser nombres de hotel.")
                return

            st.subheader("🏨 Nombres de hoteles encontrados:")
            for h3 in hoteles[:10]:
                nombre = h3.get_text(strip=True)
                if nombre:  # Asegura que no se imprima texto vacío
                    st.markdown(f"### 🏨 {nombre}")

        except Exception as e:
            st.error(f"❌ Error durante el scraping: {e}")
