import streamlit as st
from scraping_module import render_scraping

# ====================================
# 🚀 TripToIslands Admin | Entry Point
# ====================================

def main():
    # Configuración global (título y layout)
    st.set_page_config(page_title="TripToIslands Admin", layout="wide")

    # Aquí se maneja la selección principal del módulo que queremos ejecutar.
    MODULOS = {
        "Scraping": render_scraping,
        # Agrega aquí otros módulos en el futuro.
        # Ejemplo: "Analitica": render_analitica,
    }

    # Ejecutar el módulo seleccionado
    modulo_seleccionado = st.sidebar.selectbox(
        "Selecciona un módulo", list(MODULOS.keys()), key="modulo_principal"
    )

    # Ejecutar la función asociada al módulo
    MODULOS[modulo_seleccionado]()

# Punto de entrada al ejecutar streamlit_app.py
if __name__ == "__main__":
    main()
