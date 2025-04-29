import streamlit as st
from scraping_module import render as render_scraping_module
from relaciones_cpt_module import render as render_relaciones_module

# Interfaz superior de navegación principal
st.set_page_config(page_title="Panel de Control", layout="wide")
st.markdown("""
    <style>
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🌐 Panel de Control Principal")

# Menú de navegación horizontal
modulo = st.radio("", ["Relaciones CPT", "Scraping Google"], horizontal=True, index=1)

# Menú lateral según el módulo seleccionado
with st.sidebar:
    st.header("📁 Navegación")
    if modulo == "Relaciones CPT":
        st.markdown("Selecciona acciones relacionadas con CPT.")
    elif modulo == "Scraping Google":
        st.markdown("Opciones de scraping con ScraperAPI")

# Renderizar módulo correspondiente
if modulo == "Relaciones CPT":
    render_relaciones_module()
elif modulo == "Scraping Google":
    render_scraping_module()
