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

            bloques_h3 = soup.find_all("h3")
            resultados = []

            for h3 in bloques_h3:
                link_tag = h3.find_next("a", href=True)
                nombre_div = link_tag.find_next("div") if link_tag else None

                if link_tag and nombre_div:
                    enlace = link_tag["href"]
                    if enlace.startswith("/"):
                        enlace = "https://www.booking.com" + enlace
                    nombre = nombre_div.get_text(strip=True)
                    resultados.append((nombre, enlace))

            if resultados:
                st.subheader("🏨 Nombres de hoteles encontrados:")
                for nombre, enlace in resultados[:10]:
                    st.markdown(f"### 🏨 [{nombre}]({enlace})")
            else:
                st.warning("⚠️ No se pudieron encontrar nombres de hoteles en el HTML.")

        except Exception as e:
            st.error(f"❌ Error durante el scraping: {e}")
