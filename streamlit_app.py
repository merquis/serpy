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
        from drive_utils import obtener_proyectos_drive
        CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

        if proyectos:
            lista_proyectos = list(proyectos.keys())
            index_predefinido = lista_proyectos.index("TripToIslands") if "TripToIslands" in lista_proyectos else 0
            seleccion = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos, index=index_predefinido)
            st.session_state.proyecto_nombre = seleccion
            st.session_state.proyecto_id = proyectos[seleccion]

        render_scraping_google_urls()

    elif menu_principal == "Scraping Booking":
        st.title("📦 Scraping Booking")
        st.info("Esta funcionalidad estará disponible próximamente.")

    elif menu_principal == "Scraping Expedia":
        st.title("📦 Scraping Expedia")
        st.info("Esta funcionalidad estará disponible próximamente.")

    elif menu_principal == "Scraping Amazon":
        st.title("📦 Scraping Amazon")
        st.info("Esta funcionalidad estará disponible próximamente.")

if __name__ == "__main__":
    main()
