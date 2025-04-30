import streamlit as st
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup
import re

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Test mínimo con BrightData + extracción de URLs de resultados
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
        soup = BeautifulSoup(html, "html.parser")

        # Extraer solo enlaces a resultados reales (posts)
        enlaces_posts = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith("/url?q=https"):
                url_limpia = re.split(r'&', href.replace("/url?q=", ""))[0]
                if not "google.com" in url_limpia:
                    enlaces_posts.append(url_limpia)

        if enlaces_posts:
            st.success(f"🔗 Se extrajeron {len(enlaces_posts)} URLs de resultados reales.")
            for i, url in enumerate(enlaces_posts, 1):
                st.markdown(f"**{i}.** [{url}]({url})")
        else:
            st.warning("⚠️ No se encontraron enlaces de resultados reales.")

        with st.expander("📄 Ver HTML parcial"):
            st.code(html[:2000], language='html')

    except Exception as e:
        st.error(f"❌ Error al conectar vía proxy BrightData: {str(e)}")

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI con Streamlit
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google (Test mínimo con BrightData Proxy)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        st.markdown("&nbsp;")  # Espaciado visual

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google a través del proxy..."):
            testear_proxy_google(query)
