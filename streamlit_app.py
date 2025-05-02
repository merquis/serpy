import streamlit as st
from scrapers.scraping_google import render_scraping_google_urls
from scrapers.generic_scraper import (
    render_scraping_urls_manuales,
    render_scraping_etiquetas_url
)
from scrapers.booking_scraper import render_scraping_booking
from scrapers.expedia_scraper import render_scraping_expedia
from scrapers.amazon_scraper import render_scraping_amazon
from scrapers.airbnb_scraper import render_scraping_airbnb
from scrapers.tripadvisor_scraper import render_scraping_tripadvisor

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping universal",
        "Scraping específico"
    ])

    if menu_principal == "Scraping universal":
        submenu = st.sidebar.radio("Módulo Scraping", [
            "Scrapear URLs Google",
            "Scrapear URLs JSON",
            "Scrapear URLs manualmente"
        ])

        if submenu == "Scrapear URLs Google":
            render_scraping_google_urls()
        elif submenu == "Scrapear URLs JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scrapear URLs manualmente":
            render_scraping_urls_manuales()

    elif menu_principal == "Scraping específico":
        submenu = st.sidebar.radio("Scraping por dominio", [
            "Booking.com",
            "Expedia",
            "Amazon",
            "Airbnb",
            "TripAdvisor"
        ])
        if submenu == "Booking.com":
            render_scraping_booking()
        elif submenu == "Expedia":
            render_scraping_expedia()
        elif submenu == "Amazon":
            render_scraping_amazon()
        elif submenu == "Airbnb":
            render_scraping_airbnb()
        elif submenu == "TripAdvisor":
            render_scraping_tripadvisor()

if __name__ == "__main__":
    main()
