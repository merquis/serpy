# streamlit_app.py
import streamlit as st
from scraping_google_url import render_scraping_google_urls
from scraping_etiquetas_url import render_scraping_etiquetas_url
from scraping_urls_manuales import render_scraping_urls_manuales
from cpt_module import render_cpt_module

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping",
        "WordPress",
        "Próximamente"
    ])

    if 'proyecto_id' not in st.session_state:
        st.session_state.proyecto_id = None
    if 'proyecto_nombre' not in st.session_state:
        st.session_state.proyecto_nombre = None

    if menu_principal == "Scraping":
        from drive_utils import obtener_proyectos_drive
        CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

        if proyectos:
            lista_proyectos = list(proyectos.keys())
            index_predefinido = lista_proyectos.index("TripToIslands") if "TripToIslands" in lista_proyectos else 0
            seleccion = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos, index=index_predefinido)
            st.session_state.proyecto_nombre = seleccion
            st.session_state.proyecto_id = proyectos[seleccion]

        # 🔁 Nombres actualizados
        submenu = st.sidebar.radio("Módulo Scraping", [
            "Scrapear URLs Google",         # Antes: Google (términos)
            "Scrapear URLs JSON",           # Antes: Etiquetas desde archivo
            "Scrapear URLs manualmente"
        ])

        if submenu == "Scrapear URLs Google":
            render_scraping_google_urls()
        elif submenu == "Scrapear URLs JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scrapear URLs manualmente":
            render_scraping_urls_manuales()

    elif menu_principal == "WordPress":
        submenu = st.sidebar.radio("Módulo WordPress", ["CPT Manager"])
        if submenu == "CPT Manager":
            render_cpt_module()
    else:
        st.title("🚧 Módulo en desarrollo")
        st.info("Esta sección estará disponible próximamente.")

if __name__ == "__main__":
    main()
