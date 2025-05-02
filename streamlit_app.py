# streamlit_app.py
import streamlit as st
from scraping_google_url import render_scraping_google_urls
from scraping_etiquetas_url import render_scraping_etiquetas_url
from scraping_urls_manuales import render_scraping_urls_manuales
from cpt_module import render_cpt_module

# ════════════════════════════════════════════════
# 🚀 Sistema de navegación modular con submenús
# ════════════════════════════════════════════════

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")

    st.sidebar.title("🧭 Navegación")

    # Menú principal
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping Google",
        "Scraping Booking",
        "Scraping Expedia",
        "Scraping Amazon"
    ])

    # Campos comunes a los módulos de Scraping
    if 'proyecto_id' not in st.session_state:
        st.session_state.proyecto_id = None
    if 'proyecto_nombre' not in st.session_state:
        st.session_state.proyecto_nombre = None

    if menu_principal == "Scraping Google":
        submenu = st.sidebar.radio("Módulo Scraping Google", [
            "Scraping desde JSON",
            "Scraping desde URL manuales"
        ])

        if submenu == "Scraping desde JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scraping desde URL manuales":
            render_scraping_urls_manuales()

    elif menu_principal == "Scraping Booking":
        submenu = st.sidebar.radio("Módulo Scraping Booking", [
            "Scraping desde JSON",
            "Scraping desde URL manuales"
        ])

        if submenu == "Scraping desde JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scraping desde URL manuales":
            render_scraping_urls_manuales()

    elif menu_principal == "Scraping Expedia":
        submenu = st.sidebar.radio("Módulo Scraping Expedia", [
            "Scraping desde JSON",
            "Scraping desde URL manuales"
        ])

        if submenu == "Scraping desde JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scraping desde URL manuales":
            render_scraping_urls_manuales()

    elif menu_principal == "Scraping Amazon":
        submenu = st.sidebar.radio("Módulo Scraping Amazon", [
            "Scraping desde JSON",
            "Scraping desde URL manuales"
        ])

        if submenu == "Scraping desde JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scraping desde URL manuales":
            render_scraping_urls_manuales()

if __name__ == "__main__":
    main()
