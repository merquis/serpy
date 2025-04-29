"""scraping_module.py
Scraping de resultados de Google usando ScrapingAnt
"""

import streamlit as st
import requests

# Verificación de la instalación de bs4 (BeautifulSoup)
try:
    import bs4
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    st.error("❌ No se encontró el módulo 'bs4'. Asegúrate de que 'beautifulsoup4' esté en requirements.txt y haz 'Clear cache and redeploy' en Streamlit Cloud.")
    st.stop()

from urllib.parse import quote_plus

def get_google_results(query: str, api_key: str):
    search_url = f"https://www.google.es/search?q={quote_plus(query)}"
    api_url = f"https://api.scrapingant.com/v2/general?url={quote_plus(search_url)}&x-api-key={api_key}"

    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Error al hacer la petición: {e}"}

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for tag in soup.select("a"):
        href = tag.get("href")
        if href and href.startswith("/url?q="):
            clean_url = href.split("/url?q=")[-1].split("&")[0]
            if "google.com" not in clean_url and "webcache" not in clean_url:
                results.append(clean_url)
        if len(results) >= 10:
            break

    return {"results": results}

def render():
    st.title("🕸️ Scraping de Google (ScrapingAnt)")
    query = st.text_input("Frase de búsqueda")

    if st.button("Buscar") and query:
        with st.spinner("Consultando a Google..."):
            api_key = st.secrets["scrapingant"]["token"]
            result = get_google_results(query, api_key)

        if "error" in result:
            st.error(result["error"])
        else:
            st.success(f"Resultados para: '{query}'")
            for i, url in enumerate(result["results"], 1):
                st.markdown(f"{i}. [{url}]({url})")
