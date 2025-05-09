# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup


def render_scraping_booking():
    st.header("📦 Scraping de Hoteles en Booking (modelo ScrapFly)")

    location = st.text_input("📍 Ciudad destino", "Tenerife")

    if st.button("🔍 Buscar hoteles"):
        url = f"https://www.booking.com/searchresults.es.html?ss={location.replace(' ', '+')}"
        st.write(f"🔗 URL consultada: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                          " AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/117.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers)
            print(response.status_code)
            if response.status_code != 200:
                st.error(f"❌ Código de estado inesperado: {response.status_code}")
                return

            soup = BeautifulSoup(response.text, "html.parser")
            hotel_results = []

            for el in soup.find_all("div", {"data-testid": "property-card"}):
                try:
                    hotel_results.append({
                        "name": el.find("div", {"data-testid": "title"}).text.strip(),
                        "link": "https://www.booking.com" + el.find("a", {"data-testid": "title-link"})["href"],
                        "location": el.find("span", {"data-testid": "address"}).text.strip(),
                        "pricing": el.find("span", {"data-testid": "price-and-discounted-price"}).text.strip(),
                        "rating": el.find("div", {"data-testid": "review-score"}).text.strip().split(" ")[0],
                        "review_count": el.find("div", {"data-testid": "review-score"}).text.strip().split(" ")[1],
                        "thumbnail": el.find("img", {"data-testid": "image"})['src'],
                    })
                except Exception:
                    continue

            if hotel_results:
                st.subheader("🏨 Hoteles encontrados")
                for hotel in hotel_results[:10]:
                    st.markdown(f"### 🏨 [{hotel['name']}]({hotel['link']})")
                    st.write(f"📍 {hotel['location']}")
                    st.write(f"💶 {hotel['pricing']}")
                    st.write(f"⭐ {hotel['rating']} ({hotel['review_count']})")
                    st.image(hotel['thumbnail'], width=150)
                    st.markdown("---")
            else:
                st.warning("⚠️ No se encontraron hoteles en la página.")

        except Exception as e:
            st.error(f"❌ Error en la solicitud: {e}")
