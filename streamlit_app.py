# streamlit_app.py

import streamlit as st
import cpt_triptoislands as cpt
import scraping_module as scraping

# ─── CONFIGURACIÓN DE LA PÁGINA ────────────────────────────────────────────────
st.set_page_config(
    page_title="TripToIslands Panel",
    layout="wide",
)

# ─── ESTILOS DEL MENÚ SUPERIOR ───────────────────────────────────────────────
st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)

# ─── MENÚ SUPERIOR ────────────────────────────────────────────────────────────
st.markdown('<div class="menu-container">', unsafe_allow_html=True)
selected_module = st.radio(
    "", 
    ["Relaciones CPT", "Scraping Google"], 
    index=0, 
    horizontal=True, 
    label_visibility="collapsed"
)
st.markdown('</div>', unsafe_allow_html=True)

# ─── DESPLIEGUE DEL MÓDULO SELECCIONADO ──────────────────────────────────────
if selected_module == "Relaciones CPT":
    cpt.render_sidebar()
    cpt.render()
else:
    scraping.render_sidebar()
    scraping.render()
