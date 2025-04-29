# streamlit_app.py
import streamlit as st
import scraping_module as scraping

# ─── CONFIGURACIÓN DE PÁGINA ────────────────────────────────────────────────
st.set_page_config(
    page_title="TripToIslands Panel",
    layout="wide",
)

# ─── SIDEBAR Y CONTENIDO ────────────────────────────────────────────────────
scraping.render_sidebar()
scraping.render()
