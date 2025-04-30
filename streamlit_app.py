import streamlit as st
from scraping_module import render_scraping
# from otro_modulo import render_otra_funcion

st.set_page_config(page_title="TripToIslands Admin", layout="wide")

st.sidebar.title("TripToIslands · Panel Admin")
opcion = st.sidebar.selectbox("Selecciona un módulo", ["Scraping"])

if opcion == "Scraping":
    render_scraping()
# elif opcion == "Otro módulo":
#     render_otra_funcion()
