# scraper_tags_common.py

import streamlit as st
import requests
from bs4 import BeautifulSoup

# ════════════════════════════════════════════════
# 🎯 INTERFAZ: Selector visual de etiquetas HTML
# ════════════════════════════════════════════════
def seleccionar_etiquetas_html():
    opciones = {
        "title": "Title",
        "meta[name='description']": "Descripción",
        "h1": "H1",
        "h2": "H2",
        "h3": "H3"
    }

    return st.multiselect(
        "🧩 Selecciona las etiquetas HTML que deseas extraer",
        options=list(opciones.keys()),
        default=list(opciones.keys()),
        format_func=lambda x: opciones[x]
    )

# ════════════════════════════════════════════════
# 🔍 FUNCIONALIDAD: Scraping de etiquetas SEO desde una URL
# ════════════════════════════════════════════════
def scrape_tags_from_url(url, etiquetas_seleccionadas):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        resultado = {"url": url}

        for etiqueta in etiquetas_seleccionadas:
            if etiqueta == "title":
                tag = soup.find("title")
                resultado["title"] = tag.get_text(strip=True) if tag else ""

            elif etiqueta == "meta[name='description']":
                meta_tag = soup.find("meta", attrs={"name": "description"})
                resultado["description"] = meta_tag["content"].strip() if meta_tag and meta_tag.has_attr("content") else ""

            elif etiqueta in ["h1", "h2", "h3"]:
                elementos = soup.find_all(etiqueta)
                resultado[etiqueta] = [el.get_text(strip=True) for el in elementos if el.get_text(strip=True)]

        return resultado

    except Exception as e:
        return {"url": url, "error": str(e)}

# ════════════════════════════════════════════════
# 📥 EXTRA: Función para extraer URLs desde un archivo JSON (Google/Drive)
# ════════════════════════════════════════════════
def extraer_urls_de_json(datos_json):
    todas_urls = []
    for entrada in datos_json:
        urls = entrada.get("urls", [])
        if isinstance(urls, list):
            for item in urls:
                if isinstance(item, str):
                    todas_urls.append(item)
                elif isinstance(item, dict):
                    url = item.get("url")
                    if url:
                        todas_urls.append(url)
    return todas_urls
