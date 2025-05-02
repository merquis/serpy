import streamlit as st
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup
import json
from drive_utils import subir_json_a_drive

def render_scraping_google_urls():
    st.title("🔍 Scrapear URLs desde Google por término")

    query = st.text_input("🔎 Escribe términos de búsqueda (separados por comas)")
    num_results = st.selectbox("📄 Número de resultados por término", list(range(10, 101, 10)), index=0)

    if st.button("🔎 Buscar en Google"):
        proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
        ssl_context = ssl._create_unverified_context()
        resultados = []

        for termino in [q.strip() for q in query.split(",") if q.strip()]:
            urls_raw = []
            for start in range(0, int(num_results) + 10, 10):
                if len(urls_raw) >= int(num_results):
                    break
                try:
                    encoded_query = urllib.parse.quote(termino)
                    search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'
                    opener = urllib.request.build_opener(
                        urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}),
                        urllib.request.HTTPSHandler(context=ssl_context)
                    )
                    response = opener.open(search_url, timeout=15)
                    html = response.read().decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(html, "html.parser")
                    links = soup.select("a:has(h3)")
                    for a in links:
                        href = a.get("href")
                        if href and href.startswith("http") and href not in urls_raw:
                            urls_raw.append(href)
                        if len(urls_raw) >= int(num_results):
                            break
                except Exception as e:
                    st.error(f"❌ Error en '{termino}': {e}")
            resultados.append({"busqueda": termino, "urls": urls_raw})

        st.subheader("📦 Resultados encontrados")
        st.json(resultados)

        json_bytes = json.dumps(resultados, ensure_ascii=False, indent=2).encode("utf-8")

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name="resultados_google.json",
            mime="application/json"
        )

        if st.button("📤 Subir a Google Drive"):
            if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
                st.warning("⚠️ Debes seleccionar un proyecto en la barra lateral.")
                return
            enlace = subir_json_a_drive("resultados_google.json", json_bytes, st.session_state.proyecto_id)
            if enlace:
                st.success(f"✅ Subido a Drive: [Ver archivo]({enlace})")