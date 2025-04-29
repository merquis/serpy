import streamlit as st
import requests
from bs4 import BeautifulSoup

# Tu API key de ScraperAPI
API_KEY = "f1b8836788c0f99bea855e4eceb23e6d"


def render_sidebar():
    """Dibuja la barra lateral con opciones y devuelve lista de etiquetas seleccionadas."""
    st.sidebar.header("🔧 Opciones de Scraping")
    st.sidebar.info("Usa este módulo para scrapear resultados de Google")
    st.sidebar.markdown("**Etiquetas H1/H2/H3/H4**")

    etiquetas = []
    cols = st.sidebar.columns(4)
    if cols[0].checkbox("H1", key="cb_h1"): etiquetas.append("h1")
    if cols[1].checkbox("H2", key="cb_h2"): etiquetas.append("h2")
    if cols[2].checkbox("H3", key="cb_h3"): etiquetas.append("h3")
    if cols[3].checkbox("H4", key="cb_h4"): etiquetas.append("h4")

    return etiquetas


def extraer_etiquetas(url: str, etiquetas: list[str]) -> dict:
    """
    Visita la URL y extrae el texto de las etiquetas indicadas.
    Devuelve un diccionario {'h1': [...], 'h2': [...], ...} o {'error': mensaje}.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        resultados = {tag: [el.get_text(strip=True) for el in soup.find_all(tag)] for tag in etiquetas}
        return resultados
    except Exception as e:
        return {"error": str(e)}


def render(etiquetas_seleccionadas: list[str]):
    """Dibuja el cuerpo principal: inputs, consulta y resultados."""
    st.title("🔍 Scraping de Google (ScraperAPI)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input("📄 Número de resultados", min_value=1, max_value=100, value=10, step=1)

    if st.button("Buscar") and query:
        with st.spinner("Consultando a ScraperAPI..."):
            params = {"api_key": API_KEY, "query": query}
            resp = requests.get(
                "https://api.scraperapi.com/structured/google/search",
                params=params,
            )
            data = resp.json()

        if "organic_results" in data:
            total = len(data["organic_results"])
            mostrar = min(total, num_results)
            st.success(f"Se encontraron {total} resultados. Mostrando los primeros {mostrar}.")

            for i, res in enumerate(data["organic_results"][:mostrar], start=1):
                st.markdown(f"**{i}. [{res['title']}]({res['link']})**")
                st.write(res.get("snippet", ""))

                # Extracción de etiquetas si las hay
                if etiquetas_seleccionadas:
                    tags = extraer_etiquetas(res["link"], etiquetas_seleccionadas)
                    if "error" in tags:
                        st.error(f"❌ Error al analizar {res['link']}: {tags['error']}")
                    else:
                        for tag in etiquetas_seleccionadas:
                            textos = tags.get(tag, [])
                            st.markdown(f"**{tag.upper()} encontrados:**")
                            if textos:
                                for t in textos:
                                    st.markdown(f"- {t}")
                            else:
                                st.markdown(f"*No se encontraron {tag.upper()}*")
        else:
            st.warning("No se encontraron resultados.")
