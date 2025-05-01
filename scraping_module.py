import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import requests
import ssl
from drive_utils import subir_json_a_drive

# ════════════════════════════════════════════════
# 🔍 FUNCIÓN PRINCIPAL DE SCRAPING
# ════════════════════════════════════════════════

def testear_proxy_google(query, num_results, etiquetas_seleccionadas):
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
                    href = a.get('href')
                    if href and href.startswith("http"):
                        urls_raw.append(href)

            except Exception as e:
                st.error(f"❌ Error conectando con '{termino}' (start={start}): {str(e)}")
                break

        urls_finales = []
        for url in urls_raw:
            try:
                res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(res.text, 'html.parser')
                resultado = {
                    "url": url,
                    "title": soup.title.string.strip() if soup.title and soup.title.string else None,
                    "description": next((meta['content'] for meta in soup.find_all("meta") if meta.get("name", '').lower() == "description" and meta.get("content")), None)
                }

                for tag in ["h1", "h2", "h3"]:
                    if tag in etiquetas_seleccionadas:
                        resultado[tag] = [h.text.strip() for h in soup.find_all(tag)]

                urls_finales.append(resultado)

            except Exception as e:
                urls_finales.append({"url": url, "error": str(e)})

        resultados_json.append({
            "busqueda": termino,
            "urls": urls_finales
        })

    return resultados_json

# ════════════════════════════════════════════════
# 🖥️ INTERFAZ GRÁFICA DE SCRAPING
# ════════════════════════════════════════════════

def render_scraping():
    st.title("TripToIslands · Panel Admin")

    # Variables de sesión
    if 'resultados' not in st.session_state:
        st.session_state.resultados = None
    if 'nombre_archivo' not in st.session_state:
        st.session_state.nombre_archivo = None
    if 'json_bytes' not in st.session_state:
        st.session_state.json_bytes = None

    # Proyecto seleccionado
    proyecto = st.sidebar.selectbox(
        "Seleccione proyecto:",
        ["TripToIslands", "MiBebeBello"],
        index=0,
        key="proyecto_selectbox"
    )

    carpeta_id = {
        "TripToIslands": "1QS2fnsrlHxS3ZeLYvhzZqnuzx1OdRJWR",
        "MiBebeBello": "1ymfS5wfyPoPY_b9ap1sWjYrfxlDHYycI"
    }[proyecto]

    # Mostrar encabezado una sola vez
    st.sidebar.markdown("**Selecciona un módulo**")

    # Etiquetas a extraer
    st.sidebar.markdown("**Extraer etiquetas**")
    col_a, col_b, col_c = st.sidebar.columns(3)
    etiquetas = []
    if col_a.checkbox("H1", key="h1_checkbox"): etiquetas.append("h1")
    if col_b.checkbox("H2", key="h2_checkbox"): etiquetas.append("h2")
    if col_c.checkbox("H3", key="h3_checkbox"): etiquetas.append("h3")

    # Campos de búsqueda
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 Escribe tu búsqueda en Google (separa con comas)")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", list(range(10, 101, 10)), index=0, key="num_resultados")

    # Botones de acción
    col_btn, col_export, col_drive, col_reset = st.columns([1, 1, 1, 1])

    with col_btn:
        buscar = st.button("Buscar")

    with col_reset:
        if st.session_state.resultados:
            if st.button("🔄 Nueva búsqueda"):
                st.session_state.resultados = None
                st.session_state.nombre_archivo = None
                st.session_state.json_bytes = None
                st.experimental_rerun()

    # Ejecutar scraping si se hace clic en Buscar
    if buscar and query:
        with st.spinner("Consultando Google y extrayendo etiquetas..."):
            resultados = testear_proxy_google(query, int(num_results), etiquetas)
            nombre_archivo = "-".join([t.strip() for t in query.split(",")]) + ".json"
            json_bytes = json.dumps(resultados, ensure_ascii=False, indent=2).encode('utf-8')

            st.session_state.resultados = resultados
            st.session_state.nombre_archivo = nombre_archivo
            st.session_state.json_bytes = json_bytes

    # Mostrar resultados si existen
    if st.session_state.resultados:
        st.subheader("📦 Resultados en formato JSON enriquecido")
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
