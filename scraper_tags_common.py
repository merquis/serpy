import requests
from bs4 import BeautifulSoup
import streamlit as st

def scrape_tags_from_url(url, etiquetas=None):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        info = {"url": url}

        if not etiquetas:
            etiquetas = ["title", "description", "h1", "h2", "h3"]

        if "title" in etiquetas:
            info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None

        if "description" in etiquetas:
            meta = soup.find("meta", attrs={"name": "description"})
            info["description"] = meta.get("content").strip() if meta and meta.has_attr("content") else None

        if "h1" in etiquetas:
            info["h1"] = [tag.get_text(strip=True) for tag in soup.find_all("h1")]

        if "h2" in etiquetas:
            info["h2"] = [tag.get_text(strip=True) for tag in soup.find_all("h2")]

        if "h3" in etiquetas:
            info["h3"] = [tag.get_text(strip=True) for tag in soup.find_all("h3")]

        return info

    except Exception as e:
        return {"url": url, "error": str(e)}

def seleccionar_etiquetas_html():
    st.markdown("### 🏷️ Selecciona qué etiquetas deseas extraer")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: title_check = st.checkbox("title", value=True)
    with col2: desc_check = st.checkbox("description", value=True)
    with col3: h1_check = st.checkbox("h1")
    with col4: h2_check = st.checkbox("h2")
    with col5: h3_check = st.checkbox("h3")

    etiquetas = []
    if title_check: etiquetas.append("title")
    if desc_check: etiquetas.append("description")
    if h1_check: etiquetas.append("h1")
    if h2_check: etiquetas.append("h2")
    if h3_check: etiquetas.append("h3")

    if not etiquetas:
        st.warning("⚠️ Selecciona al menos una etiqueta para continuar.")
        st.stop()

    return etiquetas