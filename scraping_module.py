import streamlit as st
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping estructural con títulos y texto plano
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

        # ░░░ Extraer enlaces <a> que contienen <h3> (estructura de resultados)
        enlaces_con_titulo = soup.select("a:has(h3)")
        resultados = []
        raw_urls = []

        for a in enlaces_con_titulo:
            href = a.get("href")
            titulo = a.h3.get_text(strip=True) if a.h3 else ""
            if href and href.startswith("http"):
                resultados.append((titulo, href))
                raw_urls.append(href)

        raw_urls_unique = sorted(set(raw_urls))

        # ░░░ Mostrar resultados estructurados con título + link
        if resultados:
            st.subheader("🌐 Enlaces estructurados encontrados")
            for titulo, url in resultados:
                st.markdown(f"[{titulo}]({url})")
        else:
            st.warning("⚠️ No se encontraron enlaces estructurados en esta búsqueda.")

        # ░░░ Mostrar solo las URLs en texto plano
        if raw_urls_unique:
            st.subheader("🔗 Enlaces en texto plano (uno por línea)")
            st.text("\n".join(raw_urls_unique))

        # ░░░ HTML completo para depuración
        with st.expander("📄 Ver HTML completo de Google"):
            st.code(html, language='html')

    except Exception as e:
        st.error(f"❌ Error al conectar vía proxy BrightData: {str(e)}")

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI con Streamlit
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google (estructural + texto plano)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        st.markdown("&nbsp;")  # Espaciado visual

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google a través del proxy..."):
            testear_proxy_google(query)
