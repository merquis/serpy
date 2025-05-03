import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

# ════════════════════════════════════════════════
# 🔍 Scraping desde BrightData SERP API con multiquery
# ════════════════════════════════════════════════

def obtener_urls_google(query, num_results):
    try:
        token = st.secrets["brightdata_token"]
    except KeyError:
        st.error("❌ El token de BrightData no está definido en secrets.toml como 'brightdata_token'")
        return []

    api_url = "https://api.brightdata.com/request"
    resultados_json = []
    step = 10
    terminos = [q.strip() for q in query.split(",") if q.strip()]

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
                    st.error(f"❌ Error {response.status_code}: {response.text}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                enlaces = soup.select("a:has(h3)")
                for a in enlaces:
                    href = a.get("href")
                    if href and href.startswith("http"):
                        resultados.append(href)

                if len(resultados) >= num_results:
                    break

            except Exception as e:
                st.error(f"❌ Error con '{termino}' (start={start}): {e}")
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
# 🖥️ Interfaz Streamlit
# ════════════════════════════════════════════════

def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google con SERP API")

    if 'resultados' not in st.session_state:
        st.session_state.resultados = None
    if 'nombre_archivo' not in st.session_state:
        st.session_state.nombre_archivo = None
    if 'json_bytes' not in st.session_state:
        st.session_state.json_bytes = None
    if 'query_default' not in st.session_state:
        st.session_state.query_default = ""
    if 'num_results_default' not in st.session_state:
        st.session_state.num_results_default = 30

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("📝 Escribe tu búsqueda en Google (puedes usar varias separadas por coma)", value=st.session_state.query_default)
    with col2:
        num_results = st.slider("📄 Nº de resultados", 10, 100, st.session_state.num_results_default, 10)

    col_btn, col_new, col_export, col_drive = st.columns([1, 1, 1, 1])

    with col_btn:
        buscar = st.button("🔍 Buscar")

    with col_new:
        if st.session_state.resultados:
            if st.button("🧹 Nueva Búsqueda"):
                st.session_state.resultados = None
                st.session_state.nombre_archivo = None
                st.session_state.json_bytes = None
                st.session_state.query_default = ""
                st.session_state.num_results_default = 30
                st.experimental_rerun()

    if buscar and query:
        with st.spinner("🔄 Consultando BrightData SERP API..."):
            resultados = obtener_urls_google(query, num_results)
            nombre_archivo = "-".join([t.strip().replace(" ", "_") for t in query.split(",")]) + ".json"
            json_bytes = json.dumps(resultados, ensure_ascii=False, indent=2).encode("utf-8")

            st.session_state.resultados = resultados
            st.session_state.nombre_archivo = nombre_archivo
            st.session_state.json_bytes = json_bytes
            st.session_state.query_default = query
            st.session_state.num_results_default = num_results

    if st.session_state.resultados_
