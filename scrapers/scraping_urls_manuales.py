import streamlit as st
import json
from bs4 import BeautifulSoup
import requests
from scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url

def render_scraping_urls_manuales():
    st.title("✍️ Scrapear URLs manualmente")

    urls_raw = st.text_area("🔗 Introduce una o varias URLs separadas por comas", placeholder="https://ejemplo.com, https://otra.com")

    if not urls_raw.strip():
        return

    etiquetas = seleccionar_etiquetas_html()

    if st.button("🔎 Iniciar scraping"):
        urls = [u.strip() for u in urls_raw.split(",") if u.strip()]
        resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]
        st.subheader("📦 Resultados")
        st.json(resultados)

        json_resultado = json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8")
        st.download_button("⬇️ Descargar JSON", data=json_resultado, file_name="scraping_manual.json", mime="application/json")
