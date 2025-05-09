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

  
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        hotel_results = []
        print(soup)
        for el in soup.select("[data-testid='property-card']"):
            hotel_results.append({
                    "name": el.find("div", {"data-testid": "title"}).text.strip(),
                    "link": el.find("a", {"data-testid": "title-link"})["href"],
                    "location": el.find("span", {"data-testid": "address"}).text.strip(),
                    "pricing": el.find("span", {"data-testid": "price-and-discounted-price"}).text.strip(),
                    "rating": el.find("div", {"data-testid": "review-score"}).text.strip().split(" ")[0],
                    "review_count": el.find("div", {"data-testid": "review-score"}).text.strip().split(" ")[1],
                    "thumbnail": el.find("img", {"data-testid": "image"})['src'],
                })
        
        print(hotel_results)
