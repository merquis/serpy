# streamlit_app.py

import streamlit as st
from modules.scrapers import (
    scraping_google_url,
    scraping_urls_manuales,
    scraping_etiquetas_url,
)
from modules.cpt import cpt_module
from modules.utils.sidebar_project_selector import render_sidebar_project_selector

# ════════════════════════════════════════════════════════════════════
# 🧠 CONFIGURACIÓN GENERAL
# ════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="SERPY - Scraping SEO Inteligente", layout="wide")

# ════════════════════════════════════════════════════════════════════
# 📁 SELECCIÓN DE PROYECTO (Drive)
# ════════════════════════════════════════════════════════════════════
render_sidebar_project_selector()

# ════════════════════════════════════════════════════════════════════
# 🔍 MENÚ LATERAL DE NAVEGACIÓN
# ════════════════════════════════════════════════════════════════════
st.sidebar.markdown("### Selecciona una sección:")
seccion = st.sidebar.selectbox(
    "Sección",
    ["Scraping universal", "CPT Wordpress"],
    index=0,
    label_visibility="collapsed",
)

# ════════════════════════════════════════════════════════════════════
# 🚀 RENDER SEGÚN SECCIÓN Y MÓDULO
# ════════════════════════════════════════════════════════════════════

if seccion == "Scraping universal":
    st.sidebar.markdown("#### Módulo Scraping")
    modo = st.sidebar.radio(
        "", ["Scrapear URLs Google", "Scrapear URLs JSON", "Scrapear URLs manualmente"]
    )

    if modo == "Scrapear URLs Google":
        scraping_google_url.render_scraping_urls()

    elif modo == "Scrapear URLs JSON":
        scraping_etiquetas_url.render_scraping_etiquetas_url()

    elif modo == "Scrapear URLs manualmente":
        scraping_urls_manuales.render_scraping_urls_manuales()

elif seccion == "CPT Wordpress":
    cpt_module.render_cpt_module()
