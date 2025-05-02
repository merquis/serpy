import streamlit as st
from scraper_tags_common import scrape_tags_from_url
import json

def render_scraping_amazon():
    st.title("🛍️ Scraping Amazon")
    urls_raw = st.text_area("Pega URLs de Amazon", height=150)
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

    if st.button("Scrapear Amazon"):
        resultados = []
        for url in urls:
            datos = scrape_tags_from_url(url)
            resultados.append(datos)

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        st.download_button("⬇️ Descargar JSON", json.dumps(resultados, indent=2, ensure_ascii=False), "amazon_scraping.json", "application/json")
