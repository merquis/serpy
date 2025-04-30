import streamlit as st
import urllib.request
import urllib.parse
import ssl

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Versión mínima con proxy BrightData
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
        st.code(html[:2000], language='html')  # Muestra los primeros 2000 caracteres
        return True
    except Exception as e:
        st.error(f"❌ Error al conectar vía proxy BrightData: {str(e)}")
        return False

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI con Streamlit
# ═══════════════════════════════════════════════

def render_sidebar_scraping():
    st.sidebar.header("🔧 Opciones de Scraping")
    st.sidebar.info("Este test usa directamente el proxy BrightData y Google")
    st.sidebar.markdown("*No se realiza parsing ni extracción, solo respuesta HTML cruda.*")
    return []

def render_scraping():
    st.title("🔍 Scraping de Google (Test mínimo con BrightData Proxy)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        st.markdown("&nbsp;")  # Espaciado visual

    render_sidebar_scraping()

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google a través del proxy..."):
            testear_proxy_google(query)
