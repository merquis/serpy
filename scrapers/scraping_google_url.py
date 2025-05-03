import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json

def obtener_urls_google(query, num_results):
    token = "3c0bbe64ed94f960d1cc6a565c8424d81b98d22e4f528f28e105f9837cfd9c41"
    api_url = "https://api.brightdata.com/request"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    resultados = []
    step = 10  # Google normalmente muestra 10 resultados por página

    for start in range(0, num_results, step):
        encoded_query = urllib.parse.quote(query)
        full_url = f"https://www.google.com/search?q={encoded_query}&start={start}"

        payload = {
            "zone": "serppy",
            "url": full_url,
            "format": "raw"
        }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)

            if not response.ok:
                st.error(f"❌ Error {response.status_code}: {response.text}")
                continue

            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            enlaces = soup.select("a:has(h3)")

            for a in enlaces:
                href = a.get("href")
                if href and href.startswith("http"):
                    resultados.append(href)

        except Exception as e:
            st.error(f"❌ Error en start={start}: {e}")
            continue

    # Eliminar duplicados
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
    st.title("🔎 Scraping de URLs desde Google con SERP API")

    query = st.text_input("📝 Escribe tu búsqueda en Google")
    num_results = st.slider("📄 Nº de resultados", min_value=10, max_value=100, value=30, step=10)

    if st.button("Buscar") and query:
        with st.spinner(f"🔄 Buscando {num_results} resultados en Google..."):
            urls = obtener_urls_google(query, num_results)
            if urls:
                st.subheader("🔗 URLs encontradas:")
                st.text("\n".join(urls))
            else:
                st.warning("⚠️ No se encontraron resultados.")
