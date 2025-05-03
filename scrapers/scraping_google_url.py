import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

# ═══════════════════════════════════════════════
# 🔧 Scraping Google vía SERP API de BrightData
# ═══════════════════════════════════════════════

def obtener_urls_google(query, num_results):
    token = "3c0bbe64ed94f960d1cc6a565c8424d81b98d22e4f528f28e105f9837cfd9c41"
    api_url = "https://api.brightdata.com/request"

    encoded_query = urllib.parse.quote(query)
    full_url = f"https://www.google.com/search?q={encoded_query}"

    payload = {
        "zone": "serppy",
        "url": full_url,
        "format": "raw"
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)

        if not response.ok:
            st.error(f"❌ Error {response.status_code}: {response.text}")
            return []

        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        enlaces = soup.select("a:has(h3)")

        resultados = []
        for a in enlaces:
            href = a.get("href")
            if href and href.startswith("http"):
                resultados.append(href)

        urls_unicas = []
        vistas = set()
        for url in resultados:
            if url not in vistas:
                urls_unicas.append(url)
                vistas.add(url)
            if len(urls_unicas) >= num_results:
                break

        return urls_unicas

    except Exception as e:
        st.error(f"❌ Error al conectar con BrightData: {e}")
        return []

# ═══════════════════════════════════════════════
# 🖥️ Interfaz Streamlit
# ═══════════════════════════════════════════════

def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google con SERP API")

    query = st.text_input("📝 Escribe tu búsqueda en Google")
    num_results = st.slider("📄 Nº de resultados", min_value=10, max_value=100, value=30, step=10)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        buscar = st.button("🔍 Buscar")
    with col2:
        exportar = st.button("📤 Exportar JSON")
    with col3:
        subir = st.button("☁️ Subir a Google Drive")

    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    if buscar and query:
        with st.spinner("🔄 Consultando BrightData SERP API..."):
            urls = obtener_urls_google(query, num_results)
            resultado = {
                "busqueda": query,
                "urls": urls
            }
            st.session_state.resultados_json = [resultado]

    if st.session_state.resultados_json:
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.resultados_json)

    if exportar and st.session_state.resultados_json:
        nombre = f"resultados_{query.replace(' ', '_')}.json"
        json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ Descargar JSON", data=json_bytes, file_name=nombre, mime="application/json")

    if subir and st.session_state.resultados_json and st.session_state.get("proyecto_id"):
        nombre = f"resultados_{query.replace(' ', '_')}.json"
        json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")
        enlace = subir_json_a_drive(nombre, json_bytes, st.session_state.proyecto_id)
        if enlace:
            st.success(f"✅ Subido correctamente a Drive: [Ver archivo]({enlace})", icon="📁")
