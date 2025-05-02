import streamlit as st
from universal.scraping_google_url import render_scraping_google_urls
from universal.scraping_etiquetas_url import render_scraping_etiquetas_url
from universal.scraping_urls_manuales import render_scraping_urls_manuales
from especificos.scraping_booking import render_scraping_booking
from especificos.scraping_expedia import render_scraping_expedia
from especificos.scraping_amazon import render_scraping_amazon

def main():
    st.set_page_config(page_title="SERPY Admin", layout="wide")
    st.sidebar.title("🧭 Navegación")

    if 'proyecto_id' not in st.session_state:
        st.session_state.proyecto_id = None
    if 'proyecto_nombre' not in st.session_state:
        st.session_state.proyecto_nombre = None

    from drive_utils import obtener_proyectos_drive
    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

    if proyectos:
        lista_proyectos = list(proyectos.keys())
        index_predefinido = lista_proyectos.index("TripToIslands") if "TripToIslands" in lista_proyectos else 0
        seleccion = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos, index=index_predefinido)
        st.session_state.proyecto_nombre = seleccion
        st.session_state.proyecto_id = proyectos[seleccion]

    menu_principal = st.sidebar.selectbox("Selecciona una sección:", [
        "Scraping universal",
        "Scraping específico"
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

    elif menu_principal == "Scraping específico":
        submenu = st.sidebar.radio("Scraping por dominio", [
            "Booking.com",
            "Expedia",
            "Amazon"
        ])
        if submenu == "Booking.com":
            render_scraping_booking()
        elif submenu == "Expedia":
            render_scraping_expedia()
        elif submenu == "Amazon":
            render_scraping_amazon()

if __name__ == "__main__":
    main()
