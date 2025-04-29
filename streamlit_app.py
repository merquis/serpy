import streamlit as st
from cpt_triptoislands import render_sidebar as render_cpt_sidebar, render as render_cpt
from scraping_module import render_sidebar as render_scraping_sidebar, render as render_scraping

# ─── CONFIGURACIÓN DE PÁGINA ─────────────────────────────────────────────────────
st.set_page_config(page_title="TripToIslands Panel", layout="wide")

# ─── ESTILOS DEL MENÚ SUPERIOR ────────────────────────────────────────────────────
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

# ─── MENÚ HORIZONTAL ─────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    selected_module = st.radio(
        label="",
        options=["Relaciones CPT", "Scraping Google"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )

# ─── DESPLIEGUE SEGÚN MÓDULO SELECCIONADO ─────────────────────────────────────
if selected_module == "Relaciones CPT":
    render_cpt_sidebar()
    render_cpt()
else:
    render_scraping_sidebar()
    render_scraping()
