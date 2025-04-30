# ─────────────────────────────────────────────────────────
# SERPY – Versión 1.3.1 – Scraping Google + H1/H2/H3 opcional
# Autor: Merquis – Abril 2025
# ─────────────────────────────────────────────────────────

import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import requests

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping de Google + etiquetas SEO
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results, etiquetas_seleccionadas):
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
            try:
                res = requests.get(url, timeout=15, headers={
                    "User-Agent": "Mozilla/5.0"
                })
                soup = BeautifulSoup(res.text, 'html.parser')
                resultado = {
                    "url": url,
                    "title": soup.title.string.strip() if soup.title and soup.title.string else None,
                    "description": next((meta['content'] for meta in soup.find_all("meta") if meta.get("name", '').lower() == "description" and meta.get("content")), None)

                if "h1" in etiquetas_seleccionadas:
                    resultado["h1"] = [h.text.strip() for h in soup.find_all("h1")]
                if "h2" in etiquetas_seleccionadas:
                    resultado["h2"] = [h.text.strip() for h in soup.find_all("h2")]
                if "h3" in etiquetas_seleccionadas:
                    resultado["h3"] = [h.text.strip() for h in soup.find_all("h3")]

                urls_finales.append(resultado)
            except Exception as e:
                urls_finales.append({"url": url, "error": str(e)})

        resultados_json.append({
            "busqueda": termino,
            "urls": urls_finales
        })

    return resultados_json

# ═══════════════════════════════════════════════
# 🖥️ GUI: Streamlit con checkboxes horizontales
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google con H1/H2/H3 opcional")

    # Columna lateral
    # Eliminado selector duplicado innecesario

    st.sidebar.markdown("**Extraer etiquetas**")
    col_a, col_b, col_c = st.sidebar.columns(3)
    etiquetas = []
    if col_a.checkbox("H1"):
        etiquetas.append("h1")
    if col_b.checkbox("H2"):
        etiquetas.append("h2")
    if col_c.checkbox("H3"):
        etiquetas.append("h3")

    # Zona principal
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 Escribe tu búsqueda en Google (separa con comas)")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google y extrayendo etiquetas..."):
            resultados = testear_proxy_google(query, int(num_results), etiquetas)
            st.subheader("📦 Resultados en formato JSON enriquecido")
            st.json(resultados)
