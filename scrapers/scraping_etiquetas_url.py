
import streamlit as st
from scrapers.scraping_tags_common import render_selector_etiquetas

def render_scraping_etiquetas_url():
    st.title("🌐 Scrapear URLs desde JSON")

    st.markdown("Aquí puedes cargar un archivo JSON con URLs para scrapear etiquetas HTML.")

    etiquetas = render_selector_etiquetas(clave_estado="etiquetas_json")
    if etiquetas:
        st.success("Etiquetas seleccionadas:")
        st.json(etiquetas)
