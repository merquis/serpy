import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_archivo_json_a_proyecto

# ═══════════════════════════════════════════════
# 🔧 Scraping desde SERP API de BrightData
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
            return None, f"❌ Error {response.status_code}: {response.text}"

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

        return urls_unicas, None

    except Exception as e:
        return None, f"❌ Error al conectar con BrightData: {e}"

# ═══════════════════════════════════════════════
# 🖥️ Interfaz Streamlit
# ═══════════════════════════════════════════════

def render_scraping_urls():
    st.title("🔎 Scraping de URLs desde Google con SERP API")

    query = st.text_input("📝 Escribe tu búsqueda en Google")
    num_results = st.slider("📄 Nº de resultados", min_value=10, max_value=100, value=30, step=10)

    col1, col2, col3 = st.columns([1, 1, 1])
    ejecutar_scraping = col1.button("🔍 Buscar")
    exportar_json = col2.button("📦 Exportar JSON")
    subir_json = col3.button("📤 Subir a Google Drive")

    if ejecutar_scraping and query:
        with st.spinner("🔄 Consultando BrightData SERP API..."):
            urls, error = obtener_urls_google(query, num_results)
            if error:
                st.error(error)
                st.session_state["resultados_json"] = None
            else:
                resultado_final = [{"busqueda": query, "urls": urls}]
                st.session_state["resultados_json"] = resultado_final

    if st.session_state.get("resultados_json"):
        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state["resultados_json"])

        if exportar_json:
            nombre = f"resultados_{query.replace(' ', '_')}.json"
            contenido = json.dumps(st.session_state["resultados_json"], ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("📥 Descargar JSON", data=contenido, file_name=nombre, mime="application/json", key="descarga_json")

        if subir_json:
            if st.session_state.get("proyecto_id"):
                nombre = f"resultados_{query.replace(' ', '_')}.json"
                contenido = json.dumps(st.session_state["resultados_json"], ensure_ascii=False, indent=2).encode("utf-8")
                subir_archivo_json_a_proyecto(nombre, contenido, st.session_state["proyecto_id"])
                st.success("✅ JSON subido correctamente a Google Drive.")
            else:
                st.warning("⚠️ No se ha seleccionado un proyecto.")
