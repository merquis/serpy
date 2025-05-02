
import streamlit as st
from scrapers.scraping_tags_common import render_selector_etiquetas

def render_scraping_urls_manuales():
    st.title("✍️ Scrapear URLs manualmente")

    urls_input = st.text_area("Introduce una o varias URLs separadas por coma:")
    etiquetas = render_selector_etiquetas(clave_estado="etiquetas_manuales")

    if etiquetas:
        st.success("Etiquetas seleccionadas:")
        st.json(etiquetas)

    if st.button("Scrapear URLs"):
        urls = [url.strip() for url in urls_input.split(",") if url.strip()]
        if urls:
            st.write("🔗 URLs a scrapear:")
            st.write(urls)
        else:
            st.warning("Por favor, introduce al menos una URL válida.")
