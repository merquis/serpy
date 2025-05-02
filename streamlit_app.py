import streamlit as st
from scrapers.scraping_google_url import render_scraping_google_urls
from scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from scrapers.scraping_urls_manuales import render_scraping_urls_manuales
from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    # Inicialización del estado
    if "mostrar_input" not in st.session_state:
        st.session_state.mostrar_input = False
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = None
    if "proyecto_nombre" not in st.session_state:
        st.session_state.proyecto_nombre = "TripToIslands"
    if "proyecto_anterior" not in st.session_state:
        st.session_state.proyecto_anterior = "TripToIslands"

    # Obtener proyectos del Drive
    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
    lista_proyectos = list(proyectos.keys()) if proyectos else []

    # Priorizar TripToIslands al inicio
    if "TripToIslands" in lista_proyectos:
        lista_proyectos.remove("TripToIslands")
        lista_proyectos.insert(0, "TripToIslands")

    # Selección del proyecto actual
    if st.session_state.proyecto_nombre in lista_proyectos:
        index_predefinido = lista_proyectos.index(st.session_state.proyecto_nombre)
    else:
        index_predefinido = 0
        st.session_state.proyecto_nombre = lista_proyectos[0] if lista_proyectos else "TripToIslands"

    seleccion = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos, index=index_predefinido, key="selector_proyecto")

    st.session_state.proyecto_nombre = seleccion
    st.session_state.proyecto_id = proyectos.get(seleccion)

    # Línea divisoria + botón de creación
    st.sidebar.markdown("---")
    if st.sidebar.button("➕ Crear nuevo proyecto"):
        st.session_state.mostrar_input = True
        st.session_state.proyecto_anterior = st.session_state.proyecto_nombre

    # Campo para nombre del nuevo proyecto (solo visible si se activó)
    if st.session_state.mostrar_input:
        nuevo_nombre = st.sidebar.text_input("📝 Nombre del nuevo proyecto", key="nuevo_proyecto_nombre")
        if st.sidebar.button("Crear proyecto"):
            if nuevo_nombre.strip():
                nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                if nueva_id:
                    st.session_state.proyecto_id = nueva_id
                    st.session_state.proyecto_nombre = st.session_state.proyecto_anterior  # restaurar selección anterior
                    st.session_state.mostrar_input = False
                    st.rerun()
            else:
                st.warning("Introduce un nombre válido.")

    # Menú principal
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping universal"
    ])

    # Submenús
    if menu_principal == "Scraping universal":
        submenu = st.sidebar.radio("Módulo Scraping", [
            "Scrapear URLs Google",
            "Scrapear URLs JSON",
            "Scrapear URLs manualmente"
        ])
        if submenu == "Scrapear URLs Google":
            render_scraping_google_urls()
        elif submenu == "Scrapear URLs JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scrapear URLs manualmente":
            render_scraping_urls_manuales()

if __name__ == "__main__":
    main()
