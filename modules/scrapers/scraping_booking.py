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

            resultados = []

            divs = soup.find_all("div")
            for i in range(len(divs) - 7):
                if divs[i].name == "div":
                    try:
                        if (divs[i + 7].name == "div"
                                and divs[i + 7].get("data-testid") == "title"):
                            nombre = divs[i + 7].get_text(strip=True)
                            parent_a = divs[i + 7].find_parent("a", href=True)
                            if parent_a:
                                enlace = parent_a['href']
                                if enlace.startswith("/"):
                                    enlace = "https://www.booking.com" + enlace
                                resultados.append((nombre, enlace))
                    except Exception:
                        continue

            if resultados:
                st.subheader("🏨 Nombres de hoteles encontrados:")
                for nombre, enlace in resultados[:10]:
                    st.markdown(f"### 🏨 [{nombre}]({enlace})")
            else:
                st.warning("⚠️ No se pudieron encontrar nombres de hoteles en el HTML.")

        except Exception as e:
            st.error(f"❌ Error durante el scraping: {e}")
