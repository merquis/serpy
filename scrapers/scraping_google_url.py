import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping Google con paginación
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

    # Quitar duplicados
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

    busqueda = st.text_input("🔍 Escribe una o más búsquedas (separadas por comas)")
    num_results = st.slider("📄 Resultados por búsqueda", 10, 100, 30, step=10)

    if st.button("Buscar"):
        if not busqueda.strip():
            st.warning("⚠️ Escribe al menos una búsqueda.")
            return

        queries = [q.strip() for q in busqueda.split(",") if q.strip()]
        resultados_json = []
        raw_file = {}

        with st.spinner("🔄 Ejecutando scraping..."):
            for q in queries:
                urls = obtener_urls_google(q, num_results)
                resultados_json.append({"busqueda": q, "urls": urls})
                raw_file[q] = urls

        st.success("✅ Búsqueda completada.")
        st.subheader("📦 Resultado en formato JSON")
        st.json(resultados_json)

        # Guardar como archivo
        file_name = "resultados_scraping.json"
        contenido_bytes = json.dumps(resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        # Descargar localmente
        st.download_button("⬇️ Exportar JSON", data=contenido_bytes, file_name=file_name, mime="application/json")

        # Subir a Google Drive si hay proyecto seleccionado
        if st.button("📤 Subir a Google Drive"):
            if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
                enlace = subir_json_a_drive(file_name, contenido_bytes, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Hubo un error al subir el archivo.")
            else:
                st.warning("⚠️ No hay proyecto seleccionado.")
