import streamlit as st
import urllib.request
from bs4 import BeautifulSoup
import urllib.parse
import ssl

# ────────────────────────────── SSL BYPASS ──────────────────────────────
ssl._create_default_https_context = ssl._create_unverified_context

# ────────────────────────────── SIDEBAR ──────────────────────────────
def render_sidebar_scraping():
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
    try:
        res = urllib.request.urlopen(url, timeout=30)
        soup = BeautifulSoup(res.read(), "html.parser")
        resultados = {}
        for tag in etiquetas:
            resultados[tag] = [h.get_text(strip=True) for h in soup.find_all(tag)]
        return resultados
    except Exception as e:
        return {"error": str(e)}

# ───────────────────────────── INTERFAZ PRINCIPAL ─────────────────────────────
def render_scraping():
    st.title("🔍 Scraping de Google (BrightData Proxy)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.number_input("📄 Número de resultados", min_value=1, max_value=100, value=10, step=1)

    etiquetas_seleccionadas = render_sidebar_scraping()

    if st.button("Buscar") and query:
        with st.spinner("Consultando a BrightData..."):
            resultados = []
            per_page = 10
            proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
            proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
            opener = urllib.request.build_opener(proxy_handler)

            for start in range(0, num_results, per_page):
                cantidad = min(per_page, num_results - start)
                encoded_query = urllib.parse.quote(query)
                search_url = f"https://www.google.com/search?q={encoded_query}&start={start}&num={cantidad}"

                try:
                    response = opener.open(search_url, timeout=30)
                    soup = BeautifulSoup(response.read(), "html.parser")
                    resultados_html = soup.select("div.g")
                except Exception as e:
                    st.error(f"❌ Error al conectar o parsear resultados: {str(e)}")
                    break

                if not resultados_html:
                    st.warning(f"⚠️ No se encontraron resultados para start={start}")
                    break

                for item in resultados_html:
                    title_tag = item.select_one("h3")
                    link_tag = item.select_one("a")
                    snippet_tag = item.select_one("div.IsZvec")

                    if title_tag and link_tag:
                        resultados.append({
                            "title": title_tag.text,
                            "link": link_tag['href'],
                            "snippet": snippet_tag.text if snippet_tag else ""
                        })

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
