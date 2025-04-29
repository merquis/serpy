import streamlit as st
import requests
from bs4 import BeautifulSoup

# Clave de API de ScraperAPI (debes reemplazarla por la tuya si cambias de cuenta)
API_KEY = "f1b8836788c0f99bea855e4eceb23e6d"

# ────────────────────────────── SIDEBAR ──────────────────────────────
def render_sidebar_scraping():
    """
    Renderiza el menú lateral con opciones de etiquetas HTML (H1–H4) para extraer.
    """
    st.sidebar.header("🔧 Opciones de Scraping")
    st.sidebar.info("Usa este módulo para scrapear resultados de Google")
    st.sidebar.markdown("**Etiquetas H1/H2/H3/H4**")

    etiquetas = []
    # Distribuye los checkboxes horizontalmente en 4 columnas
    cols = st.sidebar.columns(4)
    if cols[0].checkbox("H1", key="h1_checkbox"):
        etiquetas.append("h1")
    if cols[1].checkbox("H2", key="h2_checkbox"):
        etiquetas.append("h2")
    if cols[2].checkbox("H3", key="h3_checkbox"):
        etiquetas.append("h3")
    if cols[3].checkbox("H4", key="h4_checkbox"):
        etiquetas.append("h4")

    return etiquetas  # Devuelve solo las etiquetas seleccionadas

# ────────────────────────── FUNCIONES DE EXTRACCIÓN ──────────────────────────
def extraer_etiquetas(url, etiquetas):
    """
    Dada una URL y una lista de etiquetas HTML (como h1, h2), extrae su contenido.
    """
    try:
        res = requests.get(url, timeout=10)  # Realiza una petición a la URL
        soup = BeautifulSoup(res.text, "html.parser")  # Parseo del HTML

        resultados = {}
        for tag in etiquetas:
            # Busca todas las etiquetas del tipo seleccionado y extrae su texto limpio
            resultados[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]
        return resultados
    except Exception as e:
        # Devuelve un error si falla la petición o el parseo
        return {"error": str(e)}

# ───────────────────────────── INTERFAZ PRINCIPAL ─────────────────────────────
def render_scraping():
    """
    Renderiza la interfaz principal: búsqueda, resultados, y extracción de etiquetas HTML.
    """
    st.title("🔍 Scraping de Google (ScraperAPI)")

    # Fila con dos columnas: input de búsqueda y número de resultados
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input("📄 Número de resultados", min_value=1, max_value=100, value=10, step=1)

    # Llama a la función del sidebar y obtiene las etiquetas seleccionadas
    etiquetas_seleccionadas = render_sidebar_scraping()

    # Botón para lanzar la búsqueda
    if st.button("Buscar") and query:
        with st.spinner("Consultando a ScraperAPI..."):
            payload = {
                'api_key': API_KEY,
                'query': query
            }
            # Llama al endpoint estructurado de ScraperAPI para Google Search
            r = requests.get('https://api.scraperapi.com/structured/google/search', params=payload)
            data = r.json()

            # Si hay resultados orgánicos, mostrarlos
            if "organic_results" in data:
                total = len(data['organic_results'])
                st.success(f"Se encontraron {total} resultados. Mostrando los primeros {min(num_results, total)}.")

                for i, res in enumerate(data["organic_results"][:num_results], 1):
                    st.markdown(f"**{i}. [{res['title']}]({res['link']})**\n\n{res['snippet']}")

                    # Si el usuario ha marcado etiquetas para extraer
                    if etiquetas_seleccionadas:
                        etiquetas = extraer_etiquetas(res['link'], etiquetas_seleccionadas)
                        if "error" in etiquetas:
                            st.error(f"❌ Error al analizar {res['link']}: {etiquetas['error']}")
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
