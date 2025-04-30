# ─────────────────────────────────────────────────────────
# SERPY – Versión 1.3.0 – Scrap de Google + extracción de solo H1
# Autor: Merquis – Abril 2025
# ─────────────────────────────────────────────────────────

import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import requests

def testear_proxy_google(query, num_results, extraer_h1):
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
                st.error(f"❌ Error conectando con '{termino}' (start={start}): {str(e)}")
                break

        urls_finales = []
        for url in urls_raw:
            if extraer_h1:
                try:
                    res = requests.get(url, timeout=15, headers={
                        "User-Agent": "Mozilla/5.0"
                    })
                    soup = BeautifulSoup(res.text, 'html.parser')
                    h1 = [h.text.strip() for h in soup.find_all("h1")]
                    urls_finales.append({
                        "url": url,
                        "h1": h1
                    })
                except Exception as e:
                    urls_finales.append({
                        "url": url,
                        "error": str(e)
                    })
            else:
                urls_finales.append({"url": url})

        resultados_json.append({
            "busqueda": termino,
            "urls": urls_finales
        })

    return resultados_json

def render_scraping():
    st.title("🔍 Scraping de Google con H1 opcional")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google (separa con comas)")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    extraer_h1 = st.checkbox("🔠 Extraer solo H1 de cada URL")

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google y procesando..."):
            resultados = testear_proxy_google(query, int(num_results), extraer_h1)
            st.subheader("📦 Resultados con H1 extraído")
            st.json(resultados)
