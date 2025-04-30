import streamlit as st
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup
import re

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping + extracción de URLs externas útiles
# ═══════════════════════════════════════════════

def testear_proxy_google(query):
    ssl._create_default_https_context = ssl._create_unverified_context

    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    encoded_query = urllib.parse.quote(query)
    search_url = f'https://www.google.com/search?q={encoded_query}'

    st.write(f"🔗 URL que se va a consultar: [{search_url}]({search_url})")

    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({
                'http': proxy_url,
                'https': proxy_url
            })
        )
        response = opener.open(search_url, timeout=30)
        html = response.read().decode('utf-8', errors='ignore')

        # ░░░ Extraer URLs externas ░░░
        todas_las_urls = re.findall(r'https?://[^\s"\'>]+', html)
        urls_unicas = list(set(todas_las_urls))

        # ░░░ Filtrar: eliminar URLs internas de Google
        urls_relevantes = [
            url for url in urls_unicas
            if not re.search(r'google\.(com|es)|gstatic|googleadservices|schema.org', url)
        ]

        if urls_relevantes:
            st.subheader("🌐 URLs externas detectadas (excluyendo Google)")
            for i, url in enumerate(urls_relevantes, 1):
                st.markdown(f"**{i}.** [{url}]({url})")
        else:
            st.warning("⚠️ No se encontraron URLs externas útiles (fuera de Google).")

        # ░░░ Mostrar HTML completo en expander
        with st.expander("📄 Ver HTML completo"):
            st.code(html, language='html')

    except Exception as e:
        st.error(f"❌ Error al conectar vía proxy BrightData: {str(e)}")

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI con Streamlit
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google (BrightData Proxy + URLs externas)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        st.markdown("&nbsp;")  # Espaciado visual

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google a través del proxy..."):
            testear_proxy_google(query)
