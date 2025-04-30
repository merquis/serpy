# ───────────────────────────────────────────────────────
# SERPY – Scraper Google con Streamlit + Proxy (BrightData)
# Versión 1.2.0 – Múltiples búsquedas, resultado en JSON visual
# Autor: Merquis – Abril 2025
# ───────────────────────────────────────────────────────

import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping con múltiples páginas
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results):
    """
    Realiza scraping de resultados de Google utilizando BrightData como proxy.
    Admite múltiples términos separados por coma.
    Devuelve una lista de objetos con estructura {busqueda, urls}.
    """

    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
    resultados_json = []

    # Dividir los términos por coma, limpiarlos
    terminos = [q.strip() for q in query.split(",") if q.strip()]

    for termino in terminos:
        urls = []

        for start in range(0, num_results + step, step):
            if len(urls) >= num_results:
                break

            encoded_query = urllib.parse.quote(termino)
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
                    if len(urls) >= num_results:
                        break
                    href = a.get('href')
                    if href and href.startswith("http"):
                        urls.append(href)

            except Exception as e:
                st.error(f"❌ Error al conectar con '{termino}' (start={start}): {str(e)}")
                break

        resultados_json.append({
            "busqueda": termino,
            "urls": urls
        })

    return resultados_json

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI Streamlit con selector de resultados
# ═══════════════════════════════════════════════

def render_scraping():
    """
    Interfaz de usuario para múltiples búsquedas y visualización en JSON.
    """

    st.title("🔍 Scraping de Google (multiresultado con start)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google (separa con comas)")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google..."):
            resultados = testear_proxy_google(query, int(num_results))

            # Mostrar como JSON estructurado visualmente
            st.subheader("📦 Resultados en formato JSON")
            st.json(resultados, expanded=True)
