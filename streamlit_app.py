import streamlit as st
from scrapers.scraping_google_url import render_scraping_google_urls
from scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    # ─────────────────────────────────────────────
    # 📁 Proyecto activo: selección o creación
    # ─────────────────────────────────────────────
    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

    if proyectos:
        lista_proyectos = list(proyectos.keys())
    else:
        lista_proyectos = []

    lista_proyectos.append("➕ Crear nuevo proyecto")

    seleccion = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos, key="selector_proyecto")

    if seleccion == "➕ Crear nuevo proyecto":
        nuevo_nombre = st.sidebar.text_input("📝 Nombre del nuevo proyecto", key="nuevo_proyecto_nombre")
        if st.sidebar.button("Crear proyecto"):
            if nuevo_nombre.strip():
                nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                if nueva_id:
                    st.session_state.proyecto_nombre = nuevo_nombre.strip()
                    st.session_state.proyecto_id = nueva_id
                    st.success(f"✅ Proyecto '{nuevo_nombre}' creado en Drive.")
            else:
                st.warning("Introduce un nombre válido.")
        return  # esperar a que se cree antes de continuar

    else:
        st.session_state.proyecto_nombre = seleccion
        st.session_state.proyecto_id = proyectos[seleccion]

    # ─────────────────────────────────────────────
    # Navegación de módulos
    # ─────────────────────────────────────────────
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