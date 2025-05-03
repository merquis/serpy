import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping Google desde España con BrightData usando requests
# ═══════════════════════════════════════════════

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

    # ░░░ Paso 1: Verificar IP
    try:
        r = requests.get("https://geo.brdtest.com/mygeo.json", proxies=proxies, timeout=15)
        geo = r.json()
        ip = geo.get("ip", "Desconocida")
        pais = geo.get("country_name", "Desconocido")
        st.info(f"🌍 IP de salida: {ip} | País detectado: {pais}")
    except Exception as e:
        st.warning(f"⚠️ No se pudo verificar la IP: {e}")

    # ░░░ Paso 2: Scraping de Google
    for start in range(0, num_results, step):
        encoded_query = urllib.parse.quote(query)
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

    # ░░░ Paso 3: Quitar duplicados
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
# 🖥️ INTERFAZ: Streamlit
# ═══════════════════════════════════════════════

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
