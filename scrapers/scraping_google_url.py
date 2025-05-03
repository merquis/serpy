import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

def obtener_urls_google(query, num_results):
    token = "3c0bbe64ed94f960d1cc6a565c8424d81b98d22e4f528f28e105f9837cfd9c41"
    api_url = "https://api.brightdata.com/request"
    resultados = []
    step = 10
    encoded_query = urllib.parse.quote(query)

    for start in range(0, num_results, step):
        full_url = f"https://www.google.com/search?q={encoded_query}&start={start}"
        payload = {"zone": "serppy", "url": full_url, "format": "raw"}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)
            if not response.ok:
                st.error(f"❌ Error {response.status_code}: {response.text}")
                continue

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
    st.title("🔎 Scraping de URLs desde Google con SERP API")
    query = st.text_input("📝 Escribe tu búsqueda en Google")
    num_results = st.slider("📄 Nº de resultados", 10, 100, 30, 10)

    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    # 🔘 Botones horizontales: Buscar, Exportar, Subir
    col1, col2, col3 = st.columns([1, 1, 1])
    buscar_btn = col1.button("🔍 Buscar")

    if buscar_btn and query:
        with st.spinner("🔄 Consultando BrightData SERP API..."):
            urls = obtener_urls_google(query, num_results)
            resultado = {"busqueda": query, "urls": urls}
            st.session_state.resultados_json = [resultado]

    if st.session_state.resultados_json:
        nombre = f"resultados_{query.replace(' ', '_')}.json"
        json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        # Mostrar botones horizontalmente justo debajo del botón Buscar
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.download_button("⬇️ Exportar JSON", data=json_bytes, file_name=nombre, mime="application/json")
        with col3:
            if st.button("☁️ Subir a Google Drive") and st.session_state.get("proyecto_id"):
                enlace = subir_json_a_drive(nombre, json_bytes, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Subido correctamente a Drive: [Ver archivo]({enlace})", icon="📁")

        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.resultados_json)
