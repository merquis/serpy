import streamlit as st
from scraping_urls_manuales import render_scraping_urls_manuales
from scraping_urls_json import render_scraping_urls_json
from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

# ════════════════════════════════════════════════
# 🚀 Configuración general
# ════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    # Estado inicial
    if "mostrar_input" not in st.session_state:
        st.session_state.mostrar_input = False
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = None
    if "proyecto_nombre" not in st.session_state:
        st.session_state.proyecto_nombre = "TripToIslands"
    if "nuevo_proyecto_nombre" not in st.session_state:
        st.session_state.nuevo_proyecto_nombre = ""

    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"

    # 🔄 Refrescar lista si se acaba de crear un proyecto
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

    # 📁 Gestión de proyectos
    with st.sidebar.expander("📁 Selecciona o crea un proyecto", expanded=False):
        seleccion = st.selectbox("Seleccione proyecto:", lista_proyectos, index=index_predefinido, key="selector_proyecto")

        if seleccion:
            st.session_state.proyecto_nombre = seleccion
            st.session_state.proyecto_id = proyectos.get(seleccion)

        st.markdown("---")

        nuevo_nombre = st.text_input("📄 Nombre del nuevo proyecto", key="nuevo_proyecto_nombre")
        if st.button("📂 Crear nuevo proyecto"):
            if nuevo_nombre.strip():
                nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                if nueva_id:
                    st.session_state.nuevo_proyecto_creado = nuevo_nombre.strip()
                    st.session_state.proyecto_id = nueva_id
                    st.experimental_rerun()
            else:
                st.warning("⚠️ Introduce un nombre válido para el proyecto.")

    # ════════════════════════════════════════════════
    # 🧩 Menú principal
    # ════════════════════════════════════════════════
    menu = st.sidebar.radio("🔎 Selecciona módulo", [
        "Scrapear URLs JSON",
        "Scrapear URLs manualmente"
    ])

    if menu == "Scrapear URLs JSON":
        render_scraping_urls_json()
    elif menu == "Scrapear URLs manualmente":
        render_scraping_urls_manuales()

if __name__ == "__main__":
    main()
