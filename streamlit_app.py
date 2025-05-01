# streamlit_app.py
import streamlit as st
from scraping_google_url import render_scraping_google_urls
from scraping_etiquetas_url import render_scraping_etiquetas_url
from cpt_module import render_cpt_module

# ════════════════════════════════════════════════
# 🚀 Sistema de navegación modular con submenús
# ════════════════════════════════════════════════

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")

    st.sidebar.title("🧭 Navegación")

    # Menú principal
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping",
        "WordPress",
        "Próximamente"
    ])

    # Submenús dinámicos
    if menu_principal == "Scraping":
        submenu = st.sidebar.radio("Módulo Scraping", ["Google (términos)", "URL específica"])
        if submenu == "Google (términos)":
            render_scraping_google_urls()
        elif submenu == "URL específica":
            render_scraping_etiquetas_url()

    elif menu_principal == "WordPress":
        submenu = st.sidebar.radio("Módulo WordPress", ["CPT Manager"])
        if submenu == "CPT Manager":
            render_cpt_module()

    else:
        st.title("🚧 Módulo en desarrollo")
        st.info("Esta sección estará disponible próximamente.")

if __name__ == "__main__":
    main()
