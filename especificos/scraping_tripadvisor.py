import streamlit as st
from scraper_tags_common import scrape_tags_from_url
import json

def render_scraping_tripadvisor():
    st.title("🧳 Scraping TripAdvisor")
    urls_raw = st.text_area("Pega URLs de TripAdvisor", height=150)
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

    if st.button("Scrapear TripAdvisor"):
        resultados = []
        for url in urls:
            datos = scrape_tags_from_url(url)
            resultados.append(datos)

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False),
            file_name="tripadvisor_scraping.json",
            mime="application/json"
        )
