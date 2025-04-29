import streamlit as st
import scraping_module as scraping

# ─── CONFIG ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="TripToIslands Panel", layout="wide")

# ─── MENÚ SUPERIOR ──────────────────────────────────────────────────────────────
st.markdown("""
    <style>
    .menu-container {
        display: flex;
        justify-content: center;
        margin-bottom: 2rem;
        border-bottom: 1px solid #444;
    }
    .menu-button {
        padding: 0.6rem 1.2rem;
        margin: 0 0.5rem;
        background-color: #1a1a1a;
        color: #fff;
        border: 1px solid #333;
        border-radius: 0.5rem;
        cursor: pointer;
    }
    .menu-button:hover {
        background-color: #333;
    }
    .active {
        background-color: #0074D9 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# Botones menú horizontal
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    selected = st.radio(
        "",
        ["Scraping Google"],
        horizontal=True,
        index=0,
        label_visibility="collapsed"
    )

# ─── LÓGICA DE RENDER POR MÓDULO ─────────────────────────────────────────────────
if selected == "Scraping Google":
    # Llamamos primero a la sidebar, almacenamos etiquetas
    etiquetas = scraping.render_sidebar()
    # Y luego al cuerpo pasándole esas etiquetas seleccionadas
    scraping.render(etiquetas)
