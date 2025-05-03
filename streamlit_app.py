# streamlit_app.py

import streamlit as st
from modules.scrapers.scraping_google_url import render_scraping_urls
from modules.scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from modules.scrapers.scraping_urls_manuales import render_scraping_urls_manuales
from cpt_module import render_cpt_module

# Configuración global
st.set_page_config(page_title="SERPY", layout="wide")

# Sidebar: Proyecto y navegación
st.sidebar.title("🧭 Navegación")

with st.sidebar.expander("📁 Selecciona o crea un proyecto", expanded=True):
    st.session_state.proyecto_id = "proyecto-demo"
    st.session_state.proyecto_nombre = "Proyecto de Ejemplo"

modulo = st.sidebar.selectbox("Selecciona una sección:", ["Scraping universal", "CPT Wordpress"])

if modulo == "Scraping universal":
    submodulo = st.radio("Módulo Scraping", [
        "Scrapear URLs Google",
        "Scrapear URLs JSON",
        "Scrapear URLs manualmente"
    ])

    if submodulo == "Scrapear URLs Google":
        render_scraping_urls()
    elif submodulo == "Scrapear URLs JSON":
        render_scraping_etiquetas_url()
    elif submodulo == "Scrapear URLs manualmente":
        render_scraping_urls_manuales()

elif modulo == "CPT Wordpress":
    render_cpt_module()
