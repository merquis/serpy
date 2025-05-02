
import streamlit as st
from scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url

def render_scraping_etiquetas_url():
    st.title("🕸️ Scrapear etiquetas HTML desde URLs JSON")

    urls_input = st.text_area("🔗 Pega las URLs (una por línea):")
    tags_seleccionados = seleccionar_etiquetas_html()

    if st.button("Extraer etiquetas"):
        if not urls_input.strip():
            st.warning("Introduce al menos una URL.")
            return

        urls = [url.strip() for url in urls_input.strip().splitlines() if url.strip()]
        st.info(f"Procesando {len(urls)} URLs...")

        for url in urls:
            try:
                import requests
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = scrape_tags_from_url(response.text, tags_seleccionados)
                st.subheader(f"🎯 Resultados para {url}")
                st.json(data)
            except Exception as e:
                st.error(f"Error al procesar {url}: {str(e)}")
