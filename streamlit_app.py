import streamlit as st
from scraping_google_url import render_scraping_google_urls
from scraping_etiquetas_url import render_scraping_etiquetas_url
from scraping_urls_manuales import render_scraping_urls_manuales
from cpt_module import render_cpt_module

st.set_page_config(page_title="SERPY Admin", layout="wide")
st.sidebar.title("🧭 Navegación")
menu=st.sidebar.selectbox("Sección", ["Scraping Google","Scraping Booking","Scraping Expedia","Scraping Amazon"])
if menu=="Scraping Google":
    from drive_utils import obtener_proyectos_drive
    pid=st.session_state.get('proyecto_id') or None
    if not pid:
        proj=obtener_proyectos_drive('1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy')
        sel=st.sidebar.selectbox("Proyecto", list(proj.keys()))
        st.session_state.proyecto_id=proj[sel]
    render_scraping_google_urls()
elif menu=="Scraping Booking":
    render_scraping_etiquetas_url()
elif menu=="Scraping Expedia":
    render_scraping_etiquetas_url()
elif menu=="Scraping Amazon":
    render_scraping_etiquetas_url()
