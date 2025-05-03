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

    if "query_input" not in st.session_state:
        st.session_state.query_input = ""
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    st.session_state.query_input = st.text_input("📝 Escribe tu búsqueda en Google", st.session_state.query_input)
    num_results = st.slider("📄 Nº de resultados", 10, 100, 30, 10)

    # Botones horizontales según estado
    if st.session_state.resultados_json:
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            buscar_btn = st.button("🔍 Buscar")
        with col2:
            limpiar_btn = st.button("🧹 Nueva Búsqueda")
        with col3:
            nombre_archivo = f"resultados_{st.session_state.query_input.replace(' ', '_')}.json"
            json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("⬇️ Exportar JSON", data=json_bytes, file_name=nombre_archivo, mime="application/json")
        with col4:
            if st.button("☁️ Subir a Google Drive") and st.session_state.get("proyecto_id"):
                enlace = subir_json_a_drive(nombre_archivo, json_bytes, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Subido correctamente a Drive: [Ver archivo]({enlace})", icon="📁")
    else:
        col1, _ = st.columns([1, 3])
        with col1:
            buscar_btn = st.button("🔍 Buscar")

    if 'buscar_btn' in locals() and buscar_btn and st.session_state.query_input:
        with st.spinner("🔄 Consultando BrightData SERP API..."):
            urls = obtener_urls_google(st.session_state.query_input, num_results)
            st.session_state.resultados_json = [{"busqueda": st.session_state.query_input, "urls": urls}]
        st.experimental_rerun()

    if 'limpiar_btn' in locals() and limpiar_btn:
        st.session_state.query_input = ""
        st.session_state.resultados_json = []
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.resultados_json)
