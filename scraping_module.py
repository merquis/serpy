# ─────────────────────────────────────────────────────────
# SERPY – Versión 1.3.0 – Scrap de Google + extracción de H1/H2/H3
# Autor: Merquis – Abril 2025
# ─────────────────────────────────────────────────────────

import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import requests

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping de Google + H1/H2/H3
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results, extraer_encabezados):
    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
    resultados_json = []
    terminos = [q.strip() for q in query.split(",") if q.strip()]

    for termino in terminos:
        urls_raw = []

        for start in range(0, num_results + step, step):
            if len(urls_raw) >= num_results:
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
                    if len(urls_raw) >= num_results:
                        break
                    href = a.get('href')
                    if href and href.startswith("http"):
                        urls_raw.append(href)

            except Exception as e:
                st.error(f"❌ Error al conectar con '{termino}' (start={start}): {str(e)}")
                break

        urls_expandidas = []
        for url in urls_raw:
            if extraer_encabezados:
                try:
                    res = requests.get(url, timeout=15, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    })
                    soup = BeautifulSoup(res.text, 'html.parser')
                    h1 = [h.text.strip() for h in soup.find_all("h1")]
                    h2 = [h.text.strip() for h in soup.find_all("h2")]
                    h3 = [h.text.strip() for h in soup.find_all("h3")]
                    urls_expandidas.append({
                        "url": url,
                        "h1": h1,
                        "h2": h2,
                        "h3": h3
                    })
                except Exception as e:
                    urls_expandidas.append({"url": url, "error": str(e)})
            else:
                urls_expandidas.append({"url": url})

        resultados_json.append({
            "busqueda": termino,
            "urls": urls_expandidas
        })

    return resultados_json

# ═══════════════════════════════════════════════
# 🖥️ GUI: Streamlit
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google con H1/H2/H3 opcional")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google (separa con comas)")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    extraer_h_tags = st.checkbox("🧠 Extraer H1 / H2 / H3 de cada URL")

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google y procesando URLs..."):
            resultados = testear_proxy_google(query, int(num_results), extraer_h_tags)
            st.subheader("📦 Resultados en formato JSON enriquecido")
            st.json(resultados, expanded=False)
