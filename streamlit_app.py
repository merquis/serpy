import streamlit as st
from scraping_module import render_sidebar as render_scraping_sidebar, render as render_scraping
from cpt_triptoislands import render_sidebar as render_cpt_sidebar, render as render_cpt

st.set_page_config(page_title="TripToIslands Panel", layout="wide")

# ─── MENÚ ───────────────────────────────────────────────────────────────────────
menu = st.radio("Selecciona módulo", ["Relaciones CPT", "Scraping Google"], horizontal=True)

# ─── MÓDULOS ────────────────────────────────────────────────────────────────────
if menu == "Relaciones CPT":
    site_url, post_type, per_page = render_cpt_sidebar()
    render_cpt(site_url, post_type, per_page)

elif menu == "Scraping Google":
    etiquetas = render_scraping_sidebar()
    render_scraping(etiquetas)
