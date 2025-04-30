import streamlit as st
from scraping_module import render_scraping
# from drive_utils import render_drive_panel  ← solo si haces un panel visible

st.set_page_config(page_title="TripToIslands Admin", layout="wide")

st.sidebar.title("TripToIslands · Panel Admin")
opcion = st.sidebar.selectbox("Selecciona un módulo", ["Scraping"])

if opcion == "Scraping":
    render_scraping()
# elif opcion == "Drive Utils":
#     render_drive_panel()
