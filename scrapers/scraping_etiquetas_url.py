import streamlit as st
import json
from scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url

def render_scraping_etiquetas_url():
    st.header("📄 Scrapear etiquetas desde archivo JSON")

    archivo_json = st.file_uploader("📂 Sube un archivo JSON con URLs", type=["json"])
    etiquetas_seleccionadas = seleccionar_etiquetas_html()

    if archivo_json and etiquetas_seleccionadas:
        data = json.load(archivo_json)
        urls = []
        for item in data:
            if isinstance(item, dict) and "urls" in item:
                urls.extend(item["urls"])

        urls = list(set(urls))  # Eliminar duplicados

        st.success(f"✅ {len(urls)} URLs detectadas")

        if st.button("🚀 Iniciar scraping desde archivo"):
            resultados = []
            for url in urls:
                data = scrape_tags_from_url(url, etiquetas_seleccionadas)
                resultados.append(data)

            st.success("✅ Scraping completado")
            st.write(resultados)
