import streamlit as st
import requests
from bs4 import BeautifulSoup

API_KEY = "f1b8836788c0f99bea855e4eceb23e6d"

def render_sidebar():
    st.sidebar.header("🔧 Opciones de Scraping")
    st.sidebar.info("Usa este módulo para scrapear resultados de Google")
    st.sidebar.markdown("**Etiquetas H1/H2/H3/H4**")
    etiquetas = []
    cols = st.sidebar.columns(4)
    if cols[0].checkbox("H1", key="h1"): etiquetas.append("h1")
    if cols[1].checkbox("H2", key="h2"): etiquetas.append("h2")
    if cols[2].checkbox("H3", key="h3"): etiquetas.append("h3")
    if cols[3].checkbox("H4", key="h4"): etiquetas.append("h4")
    return etiquetas

def extraer_etiquetas(url, etiquetas):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return {tag: [h.get_text(strip=True) for h in soup.find_all(tag)] for tag in etiquetas}
    except Exception as e:
        return {"error": str(e)}

def render(etiquetas_seleccionadas):
    st.title("🔍 Scraping de Google (ScraperAPI)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input("📄 Número de resultados", 1, 100, 10, 1)

    if st.button("Buscar") and query:
        with st.spinner("Consultando ScraperAPI..."):
            payload = {'api_key': API_KEY, 'query': query}
            r = requests.get('https://api.scraperapi.com/structured/google/search', params=payload)
            data = r.json()

            if "organic_results" in data:
                total = len(data['organic_results'])
                st.success(f"Se encontraron {total} resultados. Mostrando {min(num_results, total)}.")
                for i, res in enumerate(data["organic_results"][:num_results], 1):
                    st.markdown(f"**{i}. [{res['title']}]({res['link']})**\n\n{res['snippet']}")
                    if etiquetas_seleccionadas:
                        etiquetas = extraer_etiquetas(res['link'], etiquetas_seleccionadas)
                        if "error" in etiquetas:
                            st.error(f"Error al analizar {res['link']}: {etiquetas['error']}")
                        else:
                            for tag in etiquetas_seleccionadas:
                                if etiquetas[tag]:
                                    st.markdown(f"**{tag.upper()} encontrados:**")
                                    for txt in etiquetas[tag]:
                                        st.markdown(f"- {txt}")
                                else:
                                    st.markdown(f"*No se encontraron {tag.upper()}.*")
            else:
                st.warning("No se encontraron resultados.")
