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
    token = "3c0bbe64ed94f960d1cc6a565c8424d81b98d22e4f528f28e105f9837cfd9c41"
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

        payload = {
            "zone": "serppy",
            "url": search_url,
            "format": "raw"
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

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ Streamlit
# ═══════════════════════════════════════════════

def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google con SERP API")

    query = st.text_input("🔍 Escribe una o más búsquedas (separadas por comas)")
    num_results = st.slider("📄 Resultados por búsqueda", 10, 100, 30, step=10)

    # Inicializar estado
    if "scraping_resultados" not in st.session_state:
        st.session_state.scraping_resultados = None
    if "scraping_json_bytes" not in st.session_state:
        st.session_state.scraping_json_bytes = None
    if "scraping_nombre_archivo" not in st.session_state:
        st.session_state.scraping_nombre_archivo = "resultados_scraping.json"

    # Disposición horizontal de botones
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        buscar = st.button("🔍 Buscar")
    with col2:
        exportar = st.session_state.scraping_resultados is not None and st.download_button(
            "⬇️ Exportar JSON",
            data=st.session_state.scraping_json_bytes,
            file_name=st.session_state.scraping_nombre_archivo,
            mime="application/json"
        )
    with col3:
        subir = st.session_state.scraping_resultados is not None and st.button("📤 Subir a Google Drive")

    if buscar and query:
        queries = [q.strip() for q in query.split(",") if q.strip()]
        resultados_json = []

        with st.spinner("🔄 Ejecutando scraping..."):
            for q in queries:
                urls = obtener_urls_google(q, num_results)
                resultados_json.append({
                    "busqueda": q,
                    "urls": urls
                })

        # Guardar en estado
        st.session_state.scraping_resultados = resultados_json
        st.session_state.scraping_json_bytes = json.dumps(resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        nombre_archivo = f"scraping_{queries[0].replace(' ', '_')}.json" if len(queries) == 1 else "resultados_scraping.json"
        st.session_state.scraping_nombre_archivo = nombre_archivo

    # Mostrar resultados actuales si existen
    if st.session_state.scraping_resultados:
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.scraping_resultados)

    # Subir si se pulsó el botón
    if subir:
        if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
            enlace = subir_json_a_drive(
                st.session_state.scraping_nombre_archivo,
                st.session_state.scraping_json_bytes,
                st.session_state.proyecto_id
            )
            if enlace:
                st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
            else:
                st.error("❌ Error al subir el archivo.")
        else:
            st.warning("⚠️ No hay proyecto activo.")
