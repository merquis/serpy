import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

# ═══════════════════════════════════════════════
# 🔧 Scraping Google con BrightData SERP API
# ═══════════════════════════════════════════════

def obtener_urls_google(query, num_results):
    token = "TU_TOKEN_API"
    api_url = "https://api.brightdata.com/request"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    resultados = []
    step = 10

    for start in range(0, num_results, step):
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded_query}&start={start}"
        payload = {"zone": "serppy", "url": search_url, "format": "raw"}

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

    urls_unicas = list(dict.fromkeys(resultados))
    return urls_unicas[:num_results]

# ═══════════════════════════════════════════════
# 🖥️ Interfaz Streamlit
# ═══════════════════════════════════════════════

def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google con SERP API")

    query = st.text_input("🔍 Escribe una o más búsquedas (separadas por comas)")
    num_results = st.slider("📄 Resultados por búsqueda", 10, 100, 30, step=10)

    if "scraping_resultados" not in st.session_state:
        st.session_state.scraping_resultados = None
    if "scraping_json_bytes" not in st.session_state:
        st.session_state.scraping_json_bytes = None
    if "scraping_nombre_archivo" not in st.session_state:
        st.session_state.scraping_nombre_archivo = "resultados_scraping.json"

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔍 Buscar"):
            if query:
                queries = [q.strip() for q in query.split(",") if q.strip()]
                resultados_json = []

                with st.spinner("🔄 Ejecutando scraping..."):
                    for q in queries:
                        urls = obtener_urls_google(q, num_results)
                        resultados_json.append({
                            "busqueda": q,
                            "urls": urls
                        })

                st.session_state.scraping_resultados = resultados_json
                st.session_state.scraping_json_bytes = json.dumps(resultados_json, ensure_ascii=False, indent=2).encode("utf-8")
                nombre_archivo = f"scraping_{queries[0].replace(' ', '_')}.json" if len(queries) == 1 else "resultados_scraping.json"
                st.session_state.scraping_nombre_archivo = nombre_archivo

    with col2:
        if st.session_state.scraping_json_bytes:
            st.download_button(
                "⬇️ Exportar JSON",
                data=st.session_state.scraping_json_bytes,
                file_name=st.session_state.scraping_nombre_archivo,
                mime="application/json"
            )

    with col3:
        if st.session_state.scraping_json_bytes and st.button("📤 Subir a Google Drive"):
            if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
                enlace = subir_json_a_drive(
                    st.session_state.scraping_nombre_archivo,
                    st.session_state.scraping_json_bytes,
                    st.session_state.proyecto_id
                )
                if enlace:
                    st.success(f"✅ Subido a Drive: [Ver archivo]({enlace})", icon="📂")
                else:
                    st.error("❌ Error al subir a Drive")
            else:
                st.warning("⚠️ No hay proyecto activo")

    if st.session_state.scraping_resultados:
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.scraping_resultados)
