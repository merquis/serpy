import streamlit as st
from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

# Importación de los módulos refactorizados
from scraping_google_url import render_scraping_urls
from scraping_etiquetas_url import render_scraping_etiquetas_url
from scraping_urls_manuales import render_scraping_urls_manuales

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    if "mostrar_input" not in st.session_state:
        st.session_state.mostrar_input = False
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = None
    if "proyecto_nombre" not in st.session_state:
        st.session_state.proyecto_nombre = "TripToIslands"
    if "nuevo_proyecto_nombre" not in st.session_state:
        st.session_state.nuevo_proyecto_nombre = ""

    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"

    # ✅ Refrescar lista tras crear un proyecto
    if "nuevo_proyecto_creado" in st.session_state:
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
        st.session_state.proyecto_nombre = st.session_state.nuevo_proyecto_creado
        st.session_state.mostrar_input = False
        st.session_state.nuevo_proyecto_nombre = ""
        st.session_state.pop("nuevo_proyecto_creado")
        st.experimental_rerun()
    else:
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

    lista_proyectos = list(proyectos.keys()) if proyectos else []

    if "TripToIslands" in lista_proyectos:
        lista_proyectos.remove("TripToIslands")
        lista_proyectos.insert(0, "TripToIslands")

    index_predefinido = 0
    if st.session_state.proyecto_nombre in lista_proyectos:
        index_predefinido = lista_proyectos.index(st.session_state.proyecto_nombre)

    # 📁 Expander lateral para proyectos
    with st.sidebar.expander("📁 Selecciona o crea un proyecto", expanded=False):
        seleccion = st.selectbox("Proyecto actual:", lista_proyectos, index=index_predefinido)

        if seleccion:
            st.session_state.proyecto_nombre = seleccion
            st.session_state.proyecto_id = proyectos.get(seleccion)

        st.markdown("---")
        nuevo_nombre = st.text_input("📄 Nombre del nuevo proyecto", key="nuevo_proyecto_nombre")
        if st.button("📂 Crear proyecto"):
            if nuevo_nombre.strip():
                nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                if nueva_id:
                    st.session_state.nuevo_proyecto_creado = nuevo_nombre.strip()
                    st.session_state.proyecto_id = nueva_id
                    st.experimental_rerun()
            else:
                st.warning("Introduce un nombre válido.")

    # 🧩 Menú principal
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", ["Scraping universal"])

    if menu_principal == "Scraping universal":
        submenu = st.sidebar.radio("Módulo Scraping", [
            "Scrapear URLs Google",
            "Scrapear URLs JSON",
            "Scrapear URLs manualmente"
        ])
        if submenu == "Scrapear URLs Google":
            render_scraping_urls()
        elif submenu == "Scrapear URLs JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scrapear URLs manualmente":
            render_scraping_urls_manuales()

if __name__ == "__main__":
    main()
