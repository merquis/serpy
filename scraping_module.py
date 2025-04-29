import streamlit as st
import requests

def google_scraping_scraperapi(query, api_key):
    """Realiza scraping estructurado de Google usando ScraperAPI."""
    payload = {
        'api_key': api_key,
        'query': query,
    }
    try:
        response = requests.get('https://api.scraperapi.com/structured/google/search', params=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"Error de conexión: {e}")
        return {}

def render():
    st.title("Scraping de Google (ScraperAPI)")

    api_key = st.text_input("🔑 API Key de ScraperAPI", type="password")
    consulta = st.text_input("🔍 Búsqueda en Google")

    if st.button("Buscar"):
        if not api_key or not consulta:
            st.error("Debes introducir la API Key y la consulta de búsqueda.")
            return

        with st.spinner("Realizando scraping..."):
            datos = google_scraping_scraperapi(consulta, api_key)
        
        # Mostrar resultado crudo
        st.subheader("Resultado JSON bruto")
        st.json(datos)

        # Procesar y mostrar URLs principales
        st.subheader("URLs encontradas")
        if "organic_results" in datos:
            for i, resultado in enumerate(datos["organic_results"][:10], 1):
                url = resultado.get("link", "Sin URL")
                st.markdown(f"{i}. [{url}]({url})")
        else:
            st.warning("No se encontraron resultados orgánicos.")
