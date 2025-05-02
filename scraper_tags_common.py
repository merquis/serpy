import streamlit as st
from bs4 import BeautifulSoup
import requests

def seleccionar_etiquetas_html():
    return st.multiselect(
        "🧩 Selecciona las etiquetas HTML que deseas extraer",
        ["title", "meta[name='description']", "h1", "h2", "h3"],
        default=["title", "meta[name='description']", "h1"]
    )

def scrape_tags_from_url(url, etiquetas):
    resultado = {"url": url}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")

        for tag in etiquetas:
            if tag.startswith("meta"):
                meta_tag = soup.select_one(tag)
                if meta_tag and meta_tag.get("content"):
                    resultado[tag] = meta_tag["content"]
                else:
                    resultado[tag] = ""
            else:
                elementos = soup.select(tag)
                resultado[tag] = [el.get_text(strip=True) for el in elementos]
    except Exception as e:
        resultado["error"] = str(e)
    return resultado
