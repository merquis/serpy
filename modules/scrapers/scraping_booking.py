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
            soup = BeautifulSoup(response.content, 'html.parser')

            hoteles = soup.select("[data-testid='property-card']")

            if not hoteles:
                st.warning("⚠️ No se encontraron resultados usando los selectores estándar. Intentando encontrar los primeros H3 visibles...")
                posibles_nombres = soup.find_all("h3")
                if posibles_nombres:
                    st.info("🔍 Mostrando primeros encabezados H3 como posible resultado:")
                    for h3 in posibles_nombres[:10]:
                        nombre = h3.get_text(strip=True)
                        st.markdown(f"### 🏨 {nombre}")
                else:
                    st.error("❌ No se pudo encontrar ningún nombre de hotel.")
                return

            st.success(f"✅ Se encontraron {len(hoteles)} posibles bloques de hotel")
            st.subheader("🏨 Hoteles encontrados:")

            for hotel in hoteles[:10]:
                titulo = hotel.select_one('[data-testid="title"]')
                nombre = titulo.get_text(strip=True) if titulo else "Nombre no disponible"
                link = hotel.select_one("a[href]")
                enlace = "https://www.booking.com" + link["href"] if link and link["href"].startswith("/") else link["href"] if link else "Enlace no disponible"
                st.markdown(f"### 🏨 [{nombre}]({enlace})")
        except Exception as e:
            st.error(f"❌ Error durante el scraping: {e}")
