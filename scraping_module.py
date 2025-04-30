import streamlit as st
import urllib.request
import urllib.parse
import ssl
import json
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping con múltiples páginas y guardado en JSON
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results):
    ssl._create_default_https_context = ssl._create_unverified_context

    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
    resultados = []
    raw_urls = []

    for start in range(0, num_results + step, step):
        encoded_query = urllib.parse.quote(query)
        search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'

        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
            )
            response = opener.open(search_url, timeout=30)
            html = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, "html.parser")

            # Obtener todos los enlaces que contienen un título <h3>
            enlaces_con_titulo = soup.select("a:has(h3)")

            for a in enlaces_con_titulo:
                href = a.get('href')
                if href and href.startswith("http"):
                    resultados.append(href)
                    raw_urls.append(href)

        except Exception as e:
            st.error(f"❌ Error al conectar con start={start}: {str(e)}")
            continue

    # Quitar duplicados y cortar al número solicitado
    raw_urls_unicas = list(set(raw_urls))

    # ░░░ Guardar resultados en un archivo JSON
    result_data = {
        "query": query,
        "results": [{"url": url} for url in raw_urls_unicas]
    }

    with open(f"{query}_results.json", "w", encoding="utf-8") as json_file:
        json.dump(result_data, json_file, ensure_ascii=False, indent=4)

    # ░░░ Mostrar resultados de URLs
    if raw_urls_unicas:
        st.subheader("🌐 Enlaces encontrados")
        for url in raw_urls_unicas:
            st.markdown(f"[{url}]({url})")

    # ░░░ Mostrar solo URLs en texto plano
    if raw_urls_unicas:
        st.subheader("🔗 Enlaces en texto plano")
        st.text("\n".join(raw_urls_unicas))

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI Streamlit con selector de resultados
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google (multiresultado con start)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    # ░░░ GUI de selección de etiquetas SEO (sin funcionalidad para etiquetas)
    st.sidebar.header("📑 Selecciona las etiquetas SEO")
    cols = st.sidebar.columns(4)
    if cols[0].checkbox("H1"):
        pass
    if cols[1].checkbox("H2"):
        pass
    if cols[2].checkbox("H3"):
        pass
    if cols[3].checkbox("H4"):
        pass

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google..."):
            testear_proxy_google(query, int(num_results))
