# streamlit_app.py
import streamlit as st
from scrapers.scraping_google_url import render_scraping_google_urls
from scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from cpt_module import render_cpt_module

# ════════════════════════════════════════════════
# 🚀 Sistema de navegación modular con submenús
# ════════════════════════════════════════════════

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")

    st.sidebar.title("🧭 Navegación")
# ─────────────────────────────────────────────
    # 📁 Selección y creación de proyectos en Drive
    # ─────────────────────────────────────────────
    from drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"

    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
    if proyectos:
        st.sidebar.markdown("### 📁 Proyecto activo")
        lista_proyectos = list(proyectos.keys())
        seleccion = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos)
        st.session_state.proyecto_nombre = seleccion
        st.session_state.proyecto_id = proyectos[seleccion]

    st.sidebar.markdown("---")
    nuevo_nombre = st.sidebar.text_input("➕ Crear nuevo proyecto", placeholder="Nombre del nuevo proyecto")
    if st.sidebar.button("Crear proyecto"):
        if nuevo_nombre.strip():
            nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
            if nueva_id:
                st.session_state.proyecto_nombre = nuevo_nombre.strip()
                st.session_state.proyecto_id = nueva_id
                st.success(f"✅ Proyecto '{nuevo_nombre}' creado en Drive.")
        else:
            st.warning("Introduce un nombre válido.")
    else:
        st.sidebar.warning("⚠️ No se encontraron proyectos en Drive.")

    st.sidebar.markdown("---")
    nuevo_nombre = st.sidebar.text_input("➕ Crear nuevo proyecto", placeholder="Nombre del nuevo proyecto")
    if st.sidebar.button("Crear proyecto"):
        if nuevo_nombre.strip():
            nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
            if nueva_id:
                st.session_state.proyecto_nombre = nuevo_nombre.strip()
                st.session_state.proyecto_id = nueva_id
                st.success(f"✅ Proyecto '{nuevo_nombre}' creado en Drive.")
        else:
            st.warning("Introduce un nombre válido.")


    # Menú principal
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping",
        "WordPress",
        "Próximamente"
    ])

    # Campo común a todos los submódulos de Scraping: Proyecto
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
