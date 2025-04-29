import streamlit as st
import relaciones_cpt_module as relaciones
import scraping_module as scraping

# Configuración inicial
st.set_page_config(page_title="Panel de control", layout="wide")

# Menú lateral
st.sidebar.title("Navegación")
opcion = st.sidebar.radio("Elige una opción:", ["Relaciones CPT", "Scraping Google"])

# Mostrar módulo seleccionado
if opcion == "Relaciones CPT":
    relaciones.render()
elif opcion == "Scraping Google":
    scraping.render()
