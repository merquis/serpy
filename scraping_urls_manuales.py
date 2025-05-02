# scraping_urls_manuales.py
import streamlit as st
from utils_scraping import get_scraper
import json

def render_scraping_urls_manuales():
    st.title("🧬 Scraping desde URLs pegadas manualmente")

    input_urls = st.text_area("🔗 Pega URLs separadas por coma", height=150)
    etiquetas = []
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: title = st.checkbox("title")
    with col2: desc = st.checkbox("description")
    with col3: h1 = st.checkbox("H1")
    with col4: h2 = st.checkbox("H2")
    with col5: h3 = st.checkbox("H3")
    
    if title: etiquetas.append("title")
    if desc: etiquetas.append("description")
    if h1: etiquetas.append("h1")
    if h2: etiquetas.append("h2")
    if h3: etiquetas.append("h3")

    if not etiquetas:
        st.info("ℹ️ Selecciona etiquetas.")
        return

    if st.button("🔎 Extraer etiquetas"):
        urls = [u.strip() for u in input_urls.split(",") if u.strip()]
        if not urls:
            st.warning("⚠️ No se ingresaron URLs válidas.")
            return

        scraper = get_scraper("generic")
        resultados = scraper(urls, etiquetas)
        st.subheader("📦 Resultados")
        st.json(resultados)
        st.download_button(
            "⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="scraping_manual_urls.json",
            mime="application/json"
        )
