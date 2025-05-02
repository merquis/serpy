import streamlit as st
from scrapers.scraping_google_url import render_scraping_google_urls
from scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from scrapers.scraping_urls_manuales import render_scraping_urls_manuales
from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"

    if "mostrar_input" not in st.session_state:
        st.session_state.mostrar_input = False
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = None
    if "proyecto_nombre" not in st.session_state:
        st.session_state.proyecto_nombre = "TripToIslands"
    if "nuevo_proyecto_nombre" not in st.session_state:
        st.session_state.nuevo_proyecto_nombre = ""

    if "nuevo_proyecto_creado" in st.session_state:
        # 🔄 Refresca lista de proyectos tras crear uno nuevo
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
        st.session_state.proyecto_nombre = st.session_state.nuevo_proyecto_creado
        st.session_state.mostrar_input = False
        st.session_state.nuevo_proyecto_nombre = ""
        st.session_state.pop("nuevo_proyecto_creado")
        st.experimental_rerun()
    else:
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

    lista_proyectos = list(proyectos.keys()) if proyectos else []

    # Siempre poner TripToIslands al principio
    if "TripToIslands" in lista_proyectos:
        lista_proyectos.remove("TripToIslands")
        lista_proyectos.insert(0, "TripToIslands")

    # Selector de proyecto principal
    st.sidebar.subheader("Seleccione proyecto:")
    seleccion = st.sidebar.selectbox(
        "", 
        lista_proyectos,
        index=lista_proyectos.index(st.session_state.proyecto_nombre) if st.session_state.proyecto_nombre in lista_proyectos else 0,
        key="selector_proyecto"
    )

    st.session_state.proyecto_nombre = seleccion
    st.session_state.proyecto_id = proyectos.get(seleccion)

    # Sección expandible para crear nuevo proyecto
    with st.sidebar.expander("➕ Crear nuevo proyecto", expanded=False):
        st.markdown("📁 **Crear un nuevo proyecto** en Google Drive para organizar tus resultados.")
        st.caption("Puedes cambiar entre proyectos fácilmente desde el menú superior.")
        nuevo_nombre = st.text_input("📝 Nombre del proyecto", key="nuevo_proyecto_nombre")
        if st.button("📂 Crear proyecto"):
            if nuevo_nombre.strip():
                nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                if nueva_id:
                    st.session_state.nuevo_proyecto_creado = nuevo_nombre.strip()
                    st.session_state.proyecto_id = nueva_id
                    st.experimental_rerun()
            else:
                st.warning("Introduce un nombre válido.")

    # Módulo funcional
    st.sidebar.subheader("Selecciona una sección:")
    menu_principal = st.sidebar.selectbox("", ["Scraping universal"])

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
