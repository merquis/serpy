import streamlit as st
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping con múltiples páginas
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results):
   
    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
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
            response = opener.open(search_url, timeout=90)
            html = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, "html.parser")

            enlaces_con_titulo = soup.select("a:has(h3)")

            for a in enlaces_con_titulo:
                href = a.get('href')
                if href and href.startswith("http"):
                    raw_urls.append(href)

        except Exception as e:
            st.error(f"❌ Error al conectar con start={start}: {str(e)}")
            continue

    # Limitar los resultados al número solicitado
    raw_urls_unicas = raw_urls[:num_results]

    # ░░░ Mostrar solo URLs en texto plano
    if raw_urls_unicas:
        st.subheader("🔗 Enlaces en texto plano")
        st.text("\n".join(raw_urls_unicas))
    else:
        st.warning("⚠️ No se encontraron enlaces estructurados.")

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

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google..."):
            testear_proxy_google(query, int(num_results))
