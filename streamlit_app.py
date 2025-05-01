import streamlit as st
from scraping_module import render_scraping
from cpt_module import render_cpt_module

# Diccionario de módulos disponibles
MODULOS = {
    "Scraping": render_scraping,
    "CPT Wordpress": render_cpt_module,
}

def main():
    st.set_page_config(page_title="TripToIslands Admin", layout="wide")

    # Mostrar selector de módulo en sidebar
    modulo_seleccionado = st.sidebar.selectbox("Selecciona un módulo", list(MODULOS.keys()))

    # Ejecutar módulo seleccionado
    MODULOS[modulo_seleccionado]()

if __name__ == "__main__":
    main()
