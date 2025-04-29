import streamlit as st
import requests

# API Key fija
API_KEY = "f1b8836788c0f99bea855e4eceb23e6d"  # <-- Aquí ya está escrita

def google_scraping_scraperapi(query):
    """Realiza scraping estructurado de Google usando ScraperAPI."""
    payload = {
        'api_key': API_KEY,
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

    consulta = st.text_input("🔍 Escribe tu búsqueda en Google")

    if st.button("Buscar"):
        if not consulta:
            st.error("Debes introducir una búsqueda.")
            return

        with st.spinner("Realizando scraping..."):
            datos = google_scraping_scraperapi(consulta)
        
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
