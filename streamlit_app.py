import streamlit as st
from scraping_module import render_scraping
from cpt_module import render_cpt_module

MODULOS = {
    "Scraping": render_scraping,
    "CPT Wordpress": render_cpt_module,
}

def main():
    st.set_page_config(page_title="TripToIslands Admin", layout="wide")

    # SOLO AQUÍ se selecciona el módulo
    modulo = st.sidebar.selectbox("Selecciona un módulo", list(MODULOS.keys()))
    MODULOS[modulo]()

if __name__ == "__main__":
    main()
