import streamlit as st
from scrapers.scraping_google_url import render_scraping_google_urls
from scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from scrapers.scraping_urls_manuales import render_scraping_urls_manuales
from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    # Inicializar sesión
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = None
    if "proyecto_nombre" not in st.session_state:
        st.session_state.proyecto_nombre = "TripToIslands"

    # Obtener proyectos desde Drive
    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
    lista_proyectos = list(proyectos.keys()) if proyectos else []

    # Reordenar para mostrar primero TripToIslands
    if "TripToIslands" in lista_proyectos:
        lista_proyectos.remove("TripToIslands")
        lista_proyectos.insert(0, "TripToIslands")

    # Sidebar: expander único para todo el bloque de selección y creación
    with st.sidebar.expander("📁 Gestión de proyectos", expanded=True):
        st.markdown("### 🗂️ Selecciona o crea un proyecto")
        st.caption("Organiza tus datos en carpetas de Google Drive.")

        # Selector de proyecto
        if st.session_state.proyecto_nombre in lista_proyectos:
            index_predefinido = lista_proyectos.index(st.session_state.proyecto_nombre)
        else:
            index_predefinido = 0
            st.session_state.proyecto_nombre = lista_proyectos[0] if lista_proyectos else "TripToIslands"

        seleccion = st.selectbox("📌 Proyecto activo:", lista_proyectos, index=index_predefinido, key="selector_proyecto")
        st.session_state.proyecto_nombre = seleccion
        st.session_state.proyecto_id = proyectos.get(seleccion)

        # Crear nuevo proyecto
        st.markdown("#### ➕ Crear nuevo proyecto")
        nuevo_nombre = st.text_input("🔤 Nombre del proyecto", key="nuevo_proyecto_nombre")

        if st.button("🚀 Crear proyecto"):
            if nuevo_nombre.strip():
                nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                if nueva_id:
                    st.session_state.proyecto_id = nueva_id
                    st.session_state.proyecto_nombre = nuevo_nombre.strip()
                    st.success(f"✅ Proyecto '{nuevo_nombre.strip()}' creado.")
                    st.experimental_rerun()
            else:
                st.warning("⚠️ Introduce un nombre válido.")

    # Sección de módulos
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping universal"
    ])

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
