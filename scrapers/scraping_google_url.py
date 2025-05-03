import streamlit as st
import requests
import urllib.parse
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

# ═══════════════════════════════════════════════
# 🔧 Scraping desde SERP API de BrightData con formato raw
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

    if st.button("Buscar") and query:
        with st.spinner("🔄 Consultando BrightData SERP API..."):
            urls = obtener_urls_google(query, num_results)

            if urls:
                st.subheader("🔗 URLs encontradas:")
                resultado_json = [{"busqueda": query, "urls": urls}]
                st.json(resultado_json)

                if st.button("📤 Subir a Google Drive"):
                    if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
                        contenido = json.dumps(resultado_json, ensure_ascii=False, indent=2).encode("utf-8")
                        nombre = f"{query.replace(' ', '_')}.json"
                        enlace = subir_json_a_drive(nombre, contenido, st.session_state.proyecto_id)
                        if enlace:
                            st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                    else:
                        st.warning("⚠️ No hay un proyecto seleccionado para subir el archivo.")
            else:
                st.warning("⚠️ No se encontraron resultados.")
