import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup

def obtener_urls_google(query, num_results):
    proxy = 'http://brd-customer-hl_bdec3e3e-zone-serppy-country-es:o20gy6i0jgn4@brd.superproxy.io:33335'
    proxies = {
        'http': proxy,
        'https': proxy,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    resultados = []
    step = 10

    for start in range(0, num_results, step):
        encoded_query = urllib.parse.quote(query)
        # 🟢 Versión solicitada con https://
        search_url = f"https://www.google.es/search?q={encoded_query}&start={start}&hl=es&gl=es"

        try:
            response = requests.get(search_url, headers=headers, proxies=proxies, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
            enlaces = soup.select("a:has(h3)")

            for a in enlaces:
                href = a.get("href")
                if href and href.startswith("http"):
                    resultados.append(href)

        except Exception as e:
            st.error(f"❌ Error con start={start}: {e}")
            continue

    urls_unicas = []
    vistas = set()
    for url in resultados:
        if url not in vistas:
            urls_unicas.append(url)
            vistas.add(url)
        if len(urls_unicas) >= num_results:
            break

    return urls_unicas

def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google España")

    query = st.text_input("📝 Escribe tu búsqueda en Google")
    num_results = st.slider("📄 Nº de resultados", min_value=10, max_value=100, value=30, step=10)

    if st.button("Buscar") and query:
        with st.spinner("🔄 Consultando Google a través de BrightData..."):
            urls = obtener_urls_google(query, num_results)
            if urls:
                st.subheader("🔗 URLs encontradas:")
                st.text("\n".join(urls))
            else:
                st.warning("⚠️ No se encontraron resultados.")
