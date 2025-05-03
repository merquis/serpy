# scraping_google_url.py
import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

# ════════════════════════════════════════════════
# 🔍 FUNCIONALIDAD: Scraping multi-query con BrightData SERP API
# ════════════════════════════════════════════════
def obtener_urls_google_multiquery(terminos, num_results):
    token = st.secrets["brightdata_token"]
    api_url = "https://api.brightdata.com/request"
    resultados_json = []
    step = 10

    for termino in terminos:
        resultados = []
        encoded_query = urllib.parse.quote(termino)

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
                    st.error(f"❌ Error {response.status_code} para '{termino}': {response.text}")
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                enlaces = soup.select("a:has(h3)")
                for a in enlaces:
                    href = a.get("href")
                    if href and href.startswith("http"):
                        resultados.append(href)

            except Exception as e:
                st.error(f"❌ Error con '{termino}' start={start}: {e}")
                break

        # Eliminar duplicados
        urls_unicas = []
        vistas = set()
        for url in resultados:
            if url not in vistas:
                urls_unicas.append(url)
                vistas.add(url)
            if len(urls_unicas) >= num_results:
                break

        resultados_json.append({
            "busqueda": termino,
            "urls": urls_unicas
        })

    return resultados_json

# ════════════════════════════════════════════════
# 🖥️ INTERFAZ STREAMLIT
# ════════════════════════════════════════════════
def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google (multi-query con SERP API)")

    if "query_input" not in st.session_state:
        st.session_state.query_input = ""
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    col1, col2 = st.columns([3, 1])

    with col1:
        st.session_state.query_input = st.text_input(
            "📝 Escribe una o más búsquedas separadas por coma", 
            st.session_state.query_input
        )

    with col2:
        num_results = st.selectbox(
            "📄 Nº de resultados", 
            options=list(range(10, 101, 10)), 
            index=0
        )

    if st.session_state.resultados_json:
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        with col1:
            buscar_btn = st.button("🔍 Buscar")
        with col2:
            limpiar_btn = st.button("🧹 Nueva Búsqueda")
        with col3:
            nombre_archivo = "resultados_" + st.session_state.query_input.replace(" ", "_").replace(",", "-") + ".json"
            json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("⬇️ Exportar JSON", data=json_bytes, file_name=nombre_archivo, mime="application/json")
        with col4:
            if st.button("☁️ Subir a Google Drive") and st.session_state.get("proyecto_id"):
                enlace = subir_json_a_drive(nombre_archivo, json_bytes, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Subido correctamente: [Ver archivo]({enlace})", icon="📁")
    else:
        col1, _ = st.columns([1, 3])
        with col1:
            buscar_btn = st.button("🔍 Buscar")

    if 'buscar_btn' in locals() and buscar_btn and st.session_state.query_input:
        terminos = [t.strip() for t in st.session_state.query_input.split(",") if t.strip()]
        with st.spinner("🔄 Consultando BrightData SERP API..."):
            resultados = obtener_urls_google_multiquery(terminos, num_results)
            st.session_state.resultados_json = resultados
        st.experimental_rerun()

    if 'limpiar_btn' in locals() and limpiar_btn:
        st.session_state.resultados_json = []
        st.session_state.query_input = ""
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.resultados_json)
