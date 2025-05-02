import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
from drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive

# ═══════════════════════════════════════════════════════════════════
# 🔍 UNIVERSAL 1: Scrapear desde Google por término
# ═══════════════════════════════════════════════════════════════════

def render_scraping_google_urls():
    st.title("🔍 Scrapear URLs desde Google")
    query = st.text_input("🔎 Escribe tu búsqueda (separa por comas)")
    num_results = st.selectbox("📄 Nº resultados", list(range(10, 101, 10)), index=0)

    if st.button("Buscar"):
        resultados = []
        proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'

        for termino in [q.strip() for q in query.split(",") if q.strip()]:
            urls_raw = []
            for start in range(0, int(num_results) + 10, 10):
                if len(urls_raw) >= int(num_results):
                    break
                try:
                    encoded_query = requests.utils.quote(termino)
                    search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'
                    opener = requests.Session()
                    opener.proxies.update({
                        'http': proxy_url,
                        'https': proxy_url
                    })
                    headers = {"User-Agent": "Mozilla/5.0"}
                    resp = opener.get(search_url, timeout=15, headers=headers)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    links = soup.select("a:has(h3)")
                    for a in links:
                        href = a.get("href")
                        if href and href.startswith("http") and href not in urls_raw:
                            urls_raw.append(href)
                        if len(urls_raw) >= int(num_results):
                            break
                except Exception as e:
                    st.error(f"Error con término '{termino}': {e}")
            resultados.append({"busqueda": termino, "urls": urls_raw})

        st.subheader("📦 Resultados encontrados")
        st.json(resultados)

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="resultados_google.json",
            mime="application/json"
        )

# ═══════════════════════════════════════════════════════════════════
# 🔍 UNIVERSAL 2: Scrapear etiquetas desde archivo JSON (Drive o local)
# ═══════════════════════════════════════════════════════════════════

def render_scraping_etiquetas_url():
    st.title("🧬 Extraer etiquetas desde archivo JSON con URLs")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde ordenador", "Desde Drive"], horizontal=True)

    def procesar_json(crudo):
        try:
            if isinstance(crudo, bytes):
                crudo = crudo.decode("utf-8")
            return json.loads(crudo)
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")
            return None

    if fuente == "Desde ordenador":
        archivo_subido = st.file_uploader("Sube archivo JSON", type="json")
        if archivo_subido:
            st.session_state["json_contenido"] = archivo_subido.read()
            st.session_state["json_nombre"] = archivo_subido.name
    else:
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto.")
            return
        carpeta_id = st.session_state.proyecto_id
        archivos_json = listar_archivos_en_carpeta(carpeta_id)
        if archivos_json:
            archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos_json[archivo_drive])
                st.session_state["json_nombre"] = archivo_drive
        else:
            st.warning("⚠️ No hay archivos JSON disponibles.")
            return

    if "json_contenido" in st.session_state:
        st.success(f"✅ Archivo cargado: {st.session_state['json_nombre']}")
        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json:
            return

        todas_urls = []
        for entrada in datos_json:
            urls = entrada.get("urls", [])
            for u in urls:
                if isinstance(u, str):
                    todas_urls.append(u)
                elif isinstance(u, dict) and u.get("url"):
                    todas_urls.append(u["url"])

        st.markdown("### 🏷️ Etiquetas a extraer")
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: title_check = st.checkbox("title", value=True)
        with col2: desc_check = st.checkbox("description", value=True)
        with col3: h1_check = st.checkbox("h1")
        with col4: h2_check = st.checkbox("h2")
        with col5: h3_check = st.checkbox("h3")

        etiquetas = []
        if title_check: etiquetas.append("title")
        if desc_check: etiquetas.append("description")
        if h1_check: etiquetas.append("h1")
        if h2_check: etiquetas.append("h2")
        if h3_check: etiquetas.append("h3")

        if not etiquetas:
            st.warning("⚠️ Selecciona al menos una etiqueta.")
            return

        if st.button("🔎 Extraer etiquetas"):
            resultados = []
            for url in todas_urls:
                try:
                    r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                    soup = BeautifulSoup(r.text, "html.parser")
                    info = {"url": url}
                    if "title" in etiquetas:
                        info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
                    if "description" in etiquetas:
                        meta = soup.find("meta", attrs={"name": "description"})
                        info["description"] = meta["content"].strip() if meta and meta.has_attr("content") else None
                    if "h1" in etiquetas:
                        info["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")]
                    if "h2" in etiquetas:
                        info["h2"] = [h.get_text(strip=True) for h in soup.find_all("h2")]
                    if "h3" in etiquetas:
                        info["h3"] = [h.get_text(strip=True) for h in soup.find_all("h3")]
                    resultados.append(info)
                except Exception as e:
                    resultados.append({"url": url, "error": str(e)})

            st.subheader("📦 Resultados")
            st.json(resultados)

            st.download_button("⬇️ Descargar JSON", json.dumps(resultados, indent=2, ensure_ascii=False),
                               "etiquetas_extraidas.json", mime="application/json")

# ═══════════════════════════════════════════════════════════════════
# 🔍 UNIVERSAL 3: Scrapear etiquetas desde textarea
# ═══════════════════════════════════════════════════════════════════

def render_scraping_urls_manuales():
    st.title("✍️ Scrapear URLs manualmente")
    entrada = st.text_area("Pega una o varias URLs (coma o línea nueva)", height=150)
    if not entrada.strip():
        return

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: title_check = st.checkbox("title", value=True)
    with col2: desc_check = st.checkbox("description", value=True)
    with col3: h1_check = st.checkbox("h1")
    with col4: h2_check = st.checkbox("h2")
    with col5: h3_check = st.checkbox("h3")

    etiquetas = []
    if title_check: etiquetas.append("title")
    if desc_check: etiquetas.append("description")
    if h1_check: etiquetas.append("h1")
    if h2_check: etiquetas.append("h2")
    if h3_check: etiquetas.append("h3")

    if not etiquetas:
        st.warning("⚠️ Selecciona al menos una etiqueta.")
        return

    if st.button("🔎 Iniciar scraping"):
        urls = [u.strip() for u in entrada.replace(",", "\n").splitlines() if u.strip()]
        resultados = []
        for url in urls:
            try:
                r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")
                info = {"url": url}
                if "title" in etiquetas:
                    info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
                if "description" in etiquetas:
                    meta = soup.find("meta", attrs={"name": "description"})
                    info["description"] = meta["content"].strip() if meta and meta.has_attr("content") else None
                if "h1" in etiquetas:
                    info["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")]
                if "h2" in etiquetas:
                    info["h2"] = [h.get_text(strip=True) for h in soup.find_all("h2")]
                if "h3" in etiquetas:
                    info["h3"] = [h.get_text(strip=True) for h in soup.find_all("h3")]
                resultados.append(info)
            except Exception as e:
                resultados.append({"url": url, "error": str(e)})

        st.subheader("📦 Resultados")
        st.json(resultados)

        st.download_button("⬇️ Descargar JSON", json.dumps(resultados, indent=2, ensure_ascii=False),
                           "scraping_manual.json", mime="application/json")
