import streamlit as st
from scraper_tags_common import scrape_tags_from_url, seleccionar_etiquetas_html
import json

def render_scraping_expedia():
    st.title("🔍 Scraping Expedia")
    urls_raw = st.text_area("🔗 URLs de Expedia", height=200)
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]
    etiquetas = seleccionar_etiquetas_html()

    if st.button("🔎 Scrapear"):
        resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]
        st.subheader("📦 Resultados")
        st.json(resultados)
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="expedia_scraping.json",
            mime="application/json"
        )