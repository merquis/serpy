import streamlit as st
import requests

API_KEY = "f1b8836788c0f99bea855e4eceb23e6d"

def render_sidebar():
    st.sidebar.header("🔧 Opciones de Scraping")
    st.sidebar.info("Usa este módulo para scrapear resultados de Google")

def render():
    st.title("🔍 Scraping de Google (ScraperAPI)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input("📄 Resultados", min_value=1, max_value=100, value=10, step=1)

    if st.button("Buscar") and query:
        with st.spinner("Consultando a ScraperAPI..."):
            payload = {
                'api_key': API_KEY,
                'query': query
            }
            r = requests.get('https://api.scraperapi.com/structured/google/search', params=payload)
            data = r.json()

            if "organic_results" in data:
                total = len(data['organic_results'])
                st.success(f"Se encontraron {total} resultados. Mostrando los primeros {min(num_results, total)}.")
                for i, res in enumerate(data["organic_results"][:num_results], 1):
                    st.markdown(f"**{i}. [{res['title']}]({res['link']})**\n\n{res['snippet']}")
            else:
                st.warning("No se encontraron resultados.")
