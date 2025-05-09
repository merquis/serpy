import streamlit as st

# ══ MÓDULOS FUNCIONALES ══
from modules.scrapers.scraping_google_url import render_scraping_urls
from modules.scrapers.scraping_etiquetas_url import render_scraping_etiquetas_url
from modules.scrapers.scraping_urls_manuales import render_scraping_urls_manuales
from modules.scrapers.scraping_booking import render_scraping_booking  # ✅ NUEVO
from modules.cpt.cpt_module import render_cpt_module
from modules.gpt.generador_articulos_module import render_generador_articulos
from modules.gpt.chat_libre_module import render_chat_libre

from modules.utils.drive_utils import obtener_proyectos_drive, crear_carpeta_en_drive

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    # Estado inicial
    st.session_state.setdefault("mostrar_input", False)
    st.session_state.setdefault("proyecto_id", None)
    st.session_state.setdefault("proyecto_nombre", "TripToIslands")
    st.session_state.setdefault("nuevo_proyecto_nombre", "")

    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"

    # Cargar o refrescar proyectos
    if "nuevo_proyecto_creado" in st.session_state:
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
        st.session_state["proyecto_nombre"] = st.session_state["nuevo_proyecto_creado"]
        st.session_state["mostrar_input"] = False
        st.session_state["nuevo_proyecto_nombre"] = ""
        st.session_state.pop("nuevo_proyecto_creado")
        st.experimental_rerun()
    else:
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

    lista_proyectos = list(proyectos.keys()) if proyectos else []
    if "TripToIslands" in lista_proyectos:
        lista_proyectos.remove("TripToIslands")
        lista_proyectos.insert(0, "TripToIslands")

    index_predefinido = lista_proyectos.index(st.session_state["proyecto_nombre"]) if st.session_state["proyecto_nombre"] in lista_proyectos else 0

    # 📁 Selección o creación de proyecto
    with st.sidebar.expander("📁 Selecciona o crea un proyecto", expanded=False):
        seleccion = st.selectbox("Seleccione proyecto:", lista_proyectos, index=index_predefinido, key="selector_proyecto")
        if seleccion:
            st.session_state["proyecto_nombre"] = seleccion
            st.session_state["proyecto_id"] = proyectos.get(seleccion)

        st.markdown("---")

        nuevo_nombre = st.text_input("📄 Nombre del proyecto", key="nuevo_proyecto_nombre")
        if st.button("📂 Crear proyecto"):
            if nuevo_nombre.strip():
                nueva_id = crear_carpeta_en_drive(nuevo_nombre.strip(), CARPETA_SERPY_ID)
                if nueva_id:
                    st.session_state["nuevo_proyecto_creado"] = nuevo_nombre.strip()
                    st.session_state["proyecto_id"] = nueva_id
                    st.experimental_rerun()
            else:
                st.warning("Introduce un nombre válido.")

    # ══ MENÚ PRINCIPAL ══
    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping universal",
        "CPT Wordpress",
        "GPT"
    ])

    if menu_principal == "Scraping universal":
        submenu = st.sidebar.radio("Módulo Scraping", [
            "Scrapear URLs Google",
            "Scrapear URLs JSON",
            "Scrapear URLs manualmente",
            "Scraping Booking"  # ✅ NUEVA ENTRADA
        ])
        if submenu == "Scrapear URLs Google":
            render_scraping_urls()
        elif submenu == "Scrapear URLs JSON":
            render_scraping_etiquetas_url()
        elif submenu == "Scrapear URLs manualmente":
            render_scraping_urls_manuales()
        elif submenu == "Scraping Booking":
            render_scraping_booking()

    elif menu_principal == "CPT Wordpress":
        render_cpt_module()

    elif menu_principal == "GPT":
        submenu_gpt = st.sidebar.radio("Módulo GPT", [
            "Generador Maestro de Artículos",
            "Chat libre con GPT"
        ])
        if submenu_gpt == "Generador Maestro de Artículos":
            render_generador_articulos()
        elif submenu_gpt == "Chat libre con GPT":
            render_chat_libre()

if __name__ == "__main__":
    main()
