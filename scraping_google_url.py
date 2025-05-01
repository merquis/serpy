import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import ssl
from drive_utils import (
    subir_json_a_drive,
    obtener_proyectos_drive,
    crear_carpeta_en_drive
)

# ════════════════════════════════════════════════
# 🔍 SCRAPING GOOGLE: SOLO EXTRAER URLS
# ════════════════════════════════════════════════

def obtener_urls_google(query, num_results):
    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
    resultados_json = []
    terminos = [q.strip() for q in query.split(",") if q.strip()]
    ssl_context = ssl._create_unverified_context()

    for termino in terminos:
        urls_raw = []
        for start in range(0, num_results + step, step):
            if len(urls_raw) >= num_results:
                break
            encoded_query = urllib.parse.quote(termino)
            search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'
            try:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}),
                    urllib.request.HTTPSHandler(context=ssl_context)
                )
                response = opener.open(search_url, timeout=90)
                html = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, "html.parser")
                enlaces_con_titulo = soup.select("a:has(h3)")
                for a in enlaces_con_titulo:
                    if len(urls_raw) >= num_results:
                        break
                    href = a.get("href")
                    if href and href.startswith("http"):
                        urls_raw.append(href)
            except Exception as e:
                st.error(f"❌ Error conectando con '{termino}' (start={start}): {str(e)}")
                break

        resultados_json.append({"busqueda": termino, "urls": urls_raw})
    return resultados_json

# ════════════════════════════════════════════════
# 🖥️ INTERFAZ: SCRAPING SOLO URLS
# ════════════════════════════════════════════════

def render_scraping_google_urls():
    st.title("🔗 Scraping Google: Solo URLs")

    if 'resultados' not in st.session_state:
        st.session_state.resultados = None
    if 'nombre_archivo' not in st.session_state:
        st.session_state.nombre_archivo = None
    if 'json_bytes' not in st.session_state:
        st.session_state.json_bytes = None
    if 'query_default' not in st.session_state:
        st.session_state.query_default = ""
    if 'num_results_default' not in st.session_state:
        st.session_state.num_results_default = 10

    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

    if not proyectos:
        st.error("❌ No se encontraron subcarpetas en la carpeta SERPY.")
        st.stop()

    lista_proyectos = list(proyectos.keys())
    lista_proyectos.append("➕ Crear nuevo proyecto...")
    index_predefinido = lista_proyectos.index("TripToIslands") if "TripToIslands" in lista_proyectos else 0
    proyecto_seleccionado = st.sidebar.selectbox("Seleccione proyecto:", lista_proyectos, index=index_predefinido)

    if proyecto_seleccionado == "➕ Crear nuevo proyecto...":
        nuevo_nombre = st.sidebar.text_input("🆕 Nombre del nuevo proyecto")
        if nuevo_nombre and st.sidebar.button("✅ Crear y seleccionar"):
            nuevo_id = crear_carpeta_en_drive(nuevo_nombre, CARPETA_SERPY_ID)
            if nuevo_id:
                proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
                st.session_state.proyecto_manual = nuevo_nombre
                st.experimental_rerun()
        st.stop()

    proyecto = st.session_state.get("proyecto_manual", proyecto_seleccionado)
    carpeta_id = proyectos[proyecto]

    # Inputs
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 Términos de búsqueda en Google", value=st.session_state.query_default)
    with col2:
        num_results = st.selectbox("📄 Nº resultados", list(range(10, 101, 10)), index=st.session_state.num_results_default // 10 - 1)

    col_btn, col_reset, col_export, col_drive = st.columns([1, 1, 1, 1])

    with col_btn:
        buscar = st.button("🔎 Buscar")

    with col_reset:
        if st.session_state.resultados:
            if st.button("🔄 Nueva búsqueda"):
                st.session_state.resultados = None
                st.session_state.nombre_archivo = None
                st.session_state.json_bytes = None
                st.session_state.query_default = ""
                st.session_state.num_results_default = 10
                st.session_state.proyecto_manual = None
                st.experimental_rerun()

    if buscar and query:
        with st.spinner("Consultando Google y extrayendo URLs..."):
            resultados = obtener_urls_google(query, int(num_results))
            nombre_archivo = "-".join([t.strip() for t in query.split(",")]) + "_urls.json"
            json_bytes = json.dumps(resultados, ensure_ascii=False, indent=2).encode('utf-8')

            st.session_state.resultados = resultados
            st.session_state.nombre_archivo = nombre_archivo
            st.session_state.json_bytes = json_bytes
            st.session_state.query_default = query
            st.session_state.num_results_default = num_results

    if st.session_state.resultados:
        st.subheader("📦 URLs obtenidas")
        st.json(st.session_state.resultados)

        with col_export:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=st.session_state.json_bytes,
                file_name=st.session_state.nombre_archivo,
                mime="application/json"
            )

        with col_drive:
            if st.button("📤 Subir a Google Drive"):
                with st.spinner("Subiendo archivo a Google Drive..."):
                    enlace = subir_json_a_drive(
                        st.session_state.nombre_archivo,
                        st.session_state.json_bytes,
                        carpeta_id
                    )
                    if enlace:
                        st.success(f"✅ Subido correctamente: [Ver en Drive]({enlace})")
                    else:
                        st.error("❌ Error al subir el archivo a Google Drive.")
