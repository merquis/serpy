import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping de Google desde España + verificación geográfica
# ═══════════════════════════════════════════════

def obtener_urls_google(query, num_results):
    proxy = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
    resultados = []

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({'https': proxy, 'http': proxy})
    )

    # ░░░ Paso 1: Verificación de IP geográfica actual
    try:
        test_url = 'https://geo.brdtest.com/mygeo.json'
        geo_response = opener.open(test_url, timeout=15).read().decode()
        geo_info = json.loads(geo_response)
        pais = geo_info.get("country_name", "Desconocido")
        ip = geo_info.get("ip", "Desconocida")
        st.info(f"🌍 IP de salida: {ip} | País detectado: {pais}")
    except Exception as e:
        st.warning(f"⚠️ No se pudo verificar la IP: {str(e)}")

    # ░░░ Paso 2: Scraping con Google.es
    for start in range(0, num_results, step):
        encoded_query = urllib.parse.quote(query)
        search_url = f'https://www.google.es/search?q={encoded_query}&start={start}&hl=es&gl=es'

        try:
            response = opener.open(search_url, timeout=90)
            html = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, "html.parser")

            enlaces = soup.select("a:has(h3)")
            for a in enlaces:
                href = a.get("href")
                if href and href.startswith("http"):
                    resultados.append(href)

        except Exception as e:
            st.error(f"❌ Error con start={start}: {str(e)}")
            continue

    # ░░░ Eliminar duplicados y limitar cantidad
    urls_unicas = []
    vistas = set()
    for url in resultados:
        if url not in vistas:
            urls_unicas.append(url)
            vistas.add(url)
        if len(urls_unicas) >= num_results:
            break

    return urls_unicas

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ GUI Streamlit
# ═══════════════════════════════════════════════

def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google España (con verificación de IP BrightData)")

    query = st.text_input("📝 Escribe tu búsqueda en Google")
    num_results = st.slider("📄 Nº de resultados", 10, 100, 10, step=10)

    if st.button("Buscar") and query:
        with st.spinner("🔄 Conectando a través de proxy BrightData..."):
            urls = obtener_urls_google(query, num_results)
            if urls:
                st.subheader("🔗 URLs encontradas:")
                st.text("\n".join(urls))
            else:
                st.warning("⚠️ No se encontraron resultados.")
