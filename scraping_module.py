import streamlit as st
import requests
from bs4 import BeautifulSoup

API_KEY = "f1b8836788c0f99bea855e4eceb23e6d"

def render_sidebar():
    """
    Dibuja el sidebar con el multiselect de etiquetas H1–H4.
    """
    st.sidebar.header("🔧 Opciones de Scraping")
    st.sidebar.info("Usa este módulo para scrapear resultados de Google")
    st.sidebar.markdown("**Etiquetas H1/H2/H3/H4**")

    # multiselección evita duplicado de keys
    etiquetas = st.sidebar.multiselect(
        "Selecciona las etiquetas que deseas extraer:",
        ["h1", "h2", "h3", "h4"]
    )
    return etiquetas

def extraer_etiquetas(url, etiquetas):
    """
    Dada una URL y una lista de tags (h1, h2, etc), devuelve un dict
    con texto de cada etiqueta encontrada.
    """
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        resultados = {}
        for tag in etiquetas:
            resultados[tag] = [el.get_text(strip=True) for el in soup.find_all(tag)]
        return resultados
    except Exception as e:
        return {"error": str(e)}

def render():
    """
    Lógica principal: texto de búsqueda, número de resultados,
    consulta ScraperAPI y muestra resultados + extracción de etiquetas.
    """
    st.title("🔍 Scraping de Google (ScraperAPI)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input(
            "📄 Número de resultados", min_value=1, max_value=100,
            value=10, step=1
        )

    etiquetas_seleccionadas = render_sidebar()

    if st.button("Buscar") and query:
        with st.spinner("Consultando a ScraperAPI..."):
            payload = {
                'api_key': API_KEY,
                'query': query
            }
            r = requests.get(
                'https://api.scraperapi.com/structured/google/search',
                params=payload
            )
            data = r.json()

        if "organic_results" in data:
            total = len(data['organic_results'])
            st.success(
                f"Se encontraron {total} resultados. "
                f"Mostrando los primeros {min(num_results, total)}."
            )
            for i, res in enumerate(data["organic_results"][:num_results], 1):
                st.markdown(f"**{i}. [{res['title']}]({res['link']})**\n\n{res['snippet']}")

                # Si el usuario pidió extraer etiquetas, hacerlo aquí
                if etiquetas_seleccionadas:
                    etiquetas = extraer_etiquetas(res['link'], etiquetas_seleccionadas)
                    if "error" in etiquetas:
                        st.error(f"❌ Error al analizar {res['link']}: {etiquetas['error']}")
                    else:
                        for tag in etiquetas_seleccionadas:
                            items = etiquetas.get(tag, [])
                            st.markdown(f"**{tag.upper()} encontrados:**")
                            if items:
                                for txt in items:
                                    st.markdown(f"- {txt}")
                            else:
                                st.markdown(f"*No se encontraron {tag.upper()}.*")
        else:
            st.warning("No se encontraron resultados.")
