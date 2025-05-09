# modules/scrapers/scraping_booking.py

import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

def render_scraping_booking():
    st.header("📦 Scraping de Hoteles en Booking (Selenium)")

    location = st.text_input("📍 Ciudad destino", "Tenerife")

    if st.button("🔍 Buscar hoteles"):
        url = f"https://www.booking.com/searchresults.es.html?ss={location.replace(' ', '+')}"
        st.write(f"🔗 URL consultada: {url}")

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")

        try:
            driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            driver.get(url)
            time.sleep(5)  # esperar a que cargue JS

            soup = BeautifulSoup(driver.page_source, "html.parser")
            hotel_results = []

            for el in soup.find_all("div", {"data-testid": "property-card"}):
                try:
                    title_div = el.find("div", {"data-testid": "title"})
                    title_link = el.find("a", {"data-testid": "title-link"})
                    address_span = el.find("span", {"data-testid": "address"})
                    price_span = el.find("span", {"data-testid": "price-and-discounted-price"})
                    review_score_div = el.find("div", {"data-testid": "review-score"})
                    image_tag = el.find("img", {"data-testid": "image"})

                    if not all([title_div, title_link, address_span, price_span, review_score_div, image_tag]):
                        continue

                    review_parts = review_score_div.text.strip().split(" ")
                    rating = review_parts[0] if len(review_parts) > 0 else ""
                    review_count = review_parts[1] if len(review_parts) > 1 else ""

                    hotel_results.append({
                        "name": title_div.text.strip(),
                        "link": "https://www.booking.com" + title_link["href"],
                        "location": address_span.text.strip(),
                        "pricing": price_span.text.strip(),
                        "rating": rating,
                        "review_count": review_count,
                        "thumbnail": image_tag['src'],
                    })
                except Exception:
                    continue

            driver.quit()

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
