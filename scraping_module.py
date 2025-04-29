import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import urllib.parse

# Clave de API de ScraperAPI (reemplaza por la tuya si cambias de cuenta)
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
    cols = st.sidebar.columns(4)
    if cols[0].checkbox("H1", key="h1_checkbox"):
        etiquetas.append("h1")
    if cols[1].checkbox("H2", key="h2_checkbox"):
        etiquetas.append("h2")
    if cols[2].checkbox("H3", key="h3_checkbox"):
        etiquetas.append("h3")
    if cols[3].checkbox("H4", key="h4_checkbox"):
        etiquetas.append("h4")

    return etiquetas

# ────────────────────────── FUNCIONES DE EXTRACCIÓN ──────────────────────────
def extraer_etiquetas(url, etiquetas):
    """
    Dada una URL y una lista de etiquetas HTML (como h1, h2), extrae su contenido.
    """
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        resultados = {}
        for tag in etiquetas:
            resultados[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]
        return resultados
    except Exception as e:
        return {"error": str(e)}

# ───────────────────────────── INTERFAZ PRINCIPAL ─────────────────────────────
def render_scraping():
    """
    Renderiza la interfaz principal: búsqueda, resultados, y extracción de etiquetas HTML.
    """
    st.title("🔍 Scraping de Google (ScraperAPI)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input("📄 Número de resultados", min_value=1, max_value=100, value=10, step=1)

    etiquetas_seleccionadas = render_sidebar_scraping()

    if st.button("Buscar") and query:
        with st.spinner("Consultando a ScraperAPI..."):
            resultados = []
            per_page = 10

            for start in range(0, num_results, per_page):
                cantidad = min(per_page, num_results - start)
                query_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&start={start}&num={cantidad}"
                payload = {
                    'api_key': API_KEY,
                    'url': query_url,
                    'device_type': 'desktop',
                    'max_cost': '50'
                }

                r = requests.get('https://api.scraperapi.com/', params=payload)

                try:
                    data = r.json()
                except Exception as e:
                    st.error(f"❌ Error al decodificar JSON: {str(e)}")
                    st.text(r.text)
                    break

                if "organic_results" in data:
                    resultados.extend(data["organic_results"])
                elif "error" in data:
                    st.error(f"⚠️ ScraperAPI error: {data['error']}")
                    st.code(json.dumps(data, indent=2), language="json")
                    break
                else:
                    st.error(f"❌ No se encontraron resultados para start={start}")
                    st.code(json.dumps(data, indent=2), language="json")
                    break

            st.success(f"Se encontraron {len(resultados)} resultados.")
            for i, res in enumerate(resultados, 1):
                st.markdown(f"**{i}. [{res['title']}]({res['link']})**\n\n{res['snippet']}")

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
