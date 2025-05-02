import streamlit as st
from scrapers.scraping_google_url import render_scraping_google_urls
from scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    if "mostrar_input" not in st.session_state:
        st.session_state.mostrar_input = False
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = None
    if "proyecto_nombre" not in st.session_state:
        st.session_state.proyecto_nombre = None

    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
    lista_proyectos = list(proyectos.keys()) if proyectos else []
    lista_proyectos.append("➕ Crear nuevo proyecto")

    seleccion = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos, key="selector_proyecto")

    if seleccion == "➕ Crear nuevo proyecto":
        st.session_state.mostrar_input = True
    else:
        st.session_state.proyecto_nombre = seleccion
        st.session_state.proyecto_id = proyectos[seleccion]
        st.session_state.mostrar_input = False

    if st.session_state.mostrar_input:
        with st.sidebar:
            nuevo_nombre = st.text_input("📝 Nombre del nuevo proyecto", key="nuevo_proyecto_nombre")
            crear = st.button("Crear proyecto")
            if crear:
                if nuevo_nombre.strip():
                    nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                    if nueva_id:
                        st.session_state.proyecto_nombre = nuevo_nombre.strip()
                        st.session_state.proyecto_id = nueva_id
                        st.session_state["selector_proyecto"] = nuevo_nombre.strip()
                        st.session_state.mostrar_input = False
                        st.success(f"✅ Proyecto '{nuevo_nombre}' creado en Drive.")
                        st.experimental_rerun()
                else:
                    st.warning("Introduce un nombre válido.")

    # INTERFAZ PRINCIPAL (nunca debe desaparecer)
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping universal"
    ])

    if menu_principal == "Scraping universal":
        submenu = st.sidebar.radio("Módulo Scraping", [
            "Scrapear URLs Google",
            "Scrapear URLs JSON"
        ])
        if submenu == "Scrapear URLs Google":
            render_scraping_google_urls()
        elif submenu == "Scrapear URLs JSON":
            render_scraping_etiquetas_url()

if __name__ == "__main__":
    main()