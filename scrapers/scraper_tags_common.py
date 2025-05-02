
import streamlit as st

def seleccionar_etiquetas_html():
    opciones_visuales = {
        "Title": "title",
        "Descripción": "meta[name='description']",
        "H1": "h1",
        "H2": "h2",
        "H3": "h3"
    }
    seleccion = st.multiselect("🧩 Selecciona las etiquetas HTML que deseas extraer", options=list(opciones_visuales.keys()))
    return [opciones_visuales[op] for op in seleccion]

def scrape_tags_from_url(html, tags):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    resultados = {}
    for tag in tags:
        elementos = soup.select(tag)
        resultados[tag] = [el.get_text(strip=True) for el in elementos]
    return resultados
