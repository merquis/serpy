import streamlit as st
from scrapingant_client import ScrapingAntClient
from bs4 import BeautifulSoup

# Token API de ScrapingAnt
API_KEY = "7970f04a3cff4b9d89a4a287c2cd1ba2"

# ────────── Funciones ScrapingAnt ──────────
def scrape_google_search(query: str):
    """Lanza búsqueda en Google España usando ScrapingAnt Client."""
    client = ScrapingAntClient(token=API_KEY)
    target_url = f"https://www.google.es/search?q={query.replace(' ', '+')}"
    try:
        response = client.general_request(target_url)
        html_content = response.content
        return BeautifulSoup(html_content, "html.parser")
    except Exception as e:
        st.error(f"Error al conectar con ScrapingAnt: {e}")
        return None

# ────────── UI STREAMLIT ──────────
def render():
    st.title("🔎 Scraping Google España (ScrapingAnt Client)")

    query = st.text_input("Introduce tu búsqueda en Google", value="Hoteles Tenerife")
    if st.button("Buscar") and query.strip():
        with st.spinner("Buscando en Google..."):
            soup = scrape_google_search(query.strip())

        if not soup:
            return

        # Extraer resultados
        results = []
        for a in soup.select('div.yuRUbf a'):
            href = a.get('href')
            if href:
                results.append(href)

        if results:
            st.success(f"Se encontraron {len(results)} resultados:")
            for i, link in enumerate(results[:10], 1):
                st.markdown(f"{i}. [{link}]({link})")
        else:
            st.warning("⚠️ No se encontraron resultados en Google.")

