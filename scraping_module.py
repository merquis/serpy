import streamlit as st
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup
import re

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping + URLs externas útiles sin filtro por keyword
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

        # ░░░ Extraer todos los <a href="..."> externos válidos
        anchor_tags = soup.find_all("a", href=True)
        filtered_links = []

        for tag in anchor_tags:
            href = tag['href']
            if href.startswith("http"):
                if not any(block in href for block in [
                    "google", "gstatic", "accounts.google",
                    "/search?", "/url?q=", "logout", "signin"
                ]):
                    filtered_links.append(href)

        final_urls = sorted(set(filtered_links))

        if final_urls:
            st.subheader("🌐 URLs externas útiles detectadas (sin filtro por keywords)")
            for i, url in enumerate(final_urls, 1):
                st.markdown(f"**{i}.** [{url}]({url})")
        else:
            st.warning("⚠️ No se encontraron URLs externas útiles.")

        with st.expander("📄 Ver HTML completo de Google"):
            st.code(html, language='html')

    except Exception as e:
        st.error(f"❌ Error al conectar vía proxy BrightData: {str(e)}")

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI con Streamlit
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google (BrightData Proxy + URLs externas útiles)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        st.markdown("&nbsp;")  # Espaciado visual

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google a través del proxy..."):
            testear_proxy_google(query)
