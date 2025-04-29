```python
# scraping_module.py
import streamlit as st
import requests
from bs4 import BeautifulSoup

# Clave de API de ScraperAPI
API_KEY = "f1b8836788c0f99bea855e4eceb23e6d"

def render_sidebar():
    """
    Dibuja el sidebar con opciones de scraping y selección de etiquetas H1–H4.
    Devuelve la lista de etiquetas seleccionadas.
    """
    st.sidebar.header("🔧 Opciones de Scraping")
    st.sidebar.info("Usa este módulo para scrapear resultados de Google")
    st.sidebar.markdown("**Etiquetas H1/H2/H3/H4**")

    etiquetas = []
    # Usamos keys únicas para evitar duplicados
    col1, col2, col3, col4 = st.sidebar.columns(4)
    if col1.checkbox("H1", key="h1_cb"): etiquetas.append("h1")
    if col2.checkbox("H2", key="h2_cb"): etiquetas.append("h2")
    if col3.checkbox("H3", key="h3_cb"): etiquetas.append("h3")
    if col4.checkbox("H4", key="h4_cb"): etiquetas.append("h4")

    return etiquetas


def extraer_etiquetas(url, etiquetas):
    """
    Para cada etiqueta en la lista, extrae su texto de la página indicada.
    Devuelve un dict {"h1": [...], ...} o {"error": mensaje}.
    """
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        resultados = {}
        for tag in etiquetas:
            resultados[tag] = [elem.get_text(strip=True) for elem in soup.find_all(tag)]
        return resultados
    except Exception as e:
        return {"error": str(e)}


def render():
    """
    Dibuja el contenido principal: inputs de búsqueda, número de resultados y presentación.
    """
    st.title("🔍 Scraping de Google (ScraperAPI)")

    # Inputs en columnas: búsqueda y número de resultados
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input(
            "📄 Número de resultados", min_value=1, max_value=100, value=10, step=1
        )

    # Recolectar etiquetas seleccionadas
    etiquetas_seleccionadas = render_sidebar()

    if st.button("Buscar") and query:
        with st.spinner("Consultando a ScraperAPI..."):
            payload = {
                'api_key': API_KEY,
                'query': query
            }
            r = requests.get(
                'https://api.scraperapi.com/structured/google/search', params=payload
            )
            data = r.json()

            if "organic_results" in data:
                total = len(data['organic_results'])
                mostrados = min(num_results, total)
                st.success(f"Se encontraron {total} resultados. Mostrando los primeros {mostrados}.")

                for i, res in enumerate(data['organic_results'][:mostrados], 1):
                    st.markdown(f"**{i}. [{res['title']}]({res['link']})**")
                    if 'snippet' in res:
                        st.markdown(res['snippet'])

                    # Si hay etiquetas a extraer, procesar cada URL
                    if etiquetas_seleccionadas:
                        etiquetas = extraer_etiquetas(res['link'], etiquetas_seleccionadas)
                        if 'error' in etiquetas:
                            st.error(f"❌ Error al analizar {res['link']}: {etiquetas['error']}")
                        else:
                            for tag in etiquetas_seleccionadas:
                                textos = etiquetas.get(tag, [])
                                if textos:
                                    st.markdown(f"**{tag.upper()} encontrados:**")
                                    for texto in textos:
                                        st.markdown(f"- {texto}")
                                else:
                                    st.markdown(f"*No se encontraron {tag.upper()}.*")
            else:
                st.warning("No se encontraron resultados.")
```
