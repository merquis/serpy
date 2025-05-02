# scraping_etiquetas_url.py
import json
import streamlit as st
from drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive
from utils_scraping import get_scraper

def render_scraping_etiquetas_url():
    st.title("🧬 Scraping de URLs desde archivo JSON")
    fuente = st.radio("Selecciona fuente del archivo:", ["Desde ordenador", "Desde Drive"], horizontal=True)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("Sube archivo JSON", type="json")
        if archivo:
            st.session_state["json_contenido"] = archivo.read()
            st.session_state["json_nombre"] = archivo.name
    else:
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto.")
            return

        archivos = listar_archivos_en_carpeta(st.session_state.proyecto_id)
        if archivos:
            seleccion = st.selectbox("Archivo JSON", list(archivos.keys()))
            if st.button("📥 Cargar"):
                st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos[seleccion])
                st.session_state["json_nombre"] = seleccion
        else:
            st.warning("⚠️ No hay archivos JSON.")

    if "json_contenido" in st.session_state:
        st.success(f"✅ Archivo cargado: {st.session_state['json_nombre']}")
        try:
            data = json.loads(st.session_state["json_contenido"])
        except Exception as e:
            st.error(f"❌ Error leyendo el archivo: {e}")
            return

        urls = []
        for entrada in data:
            for u in entrada.get("urls", []):
                if isinstance(u, str):
                    urls.append(u)
                elif isinstance(u, dict) and "url" in u:
                    urls.append(u["url"])

        if not urls:
            st.warning("⚠️ No se encontraron URLs.")
            return

        etiquetas = []
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: title = st.checkbox("title")
        with col2: desc = st.checkbox("description")
        with col3: h1 = st.checkbox("H1")
        with col4: h2 = st.checkbox("H2")
        with col5: h3 = st.checkbox("H3")
        if title: etiquetas.append("title")
        if desc: etiquetas.append("description")
        if h1: etiquetas.append("h1")
        if h2: etiquetas.append("h2")
        if h3: etiquetas.append("h3")

        if not etiquetas:
            st.info("ℹ️ Selecciona etiquetas.")
            return

        if st.button("🔎 Extraer"):
            scraper = get_scraper("generic")
            resultados = scraper(urls, etiquetas)
            st.subheader("📦 Resultados")
            st.json(resultados)
            st.download_button(
                "⬇️ Descargar JSON",
                data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name="etiquetas_extraidas.json",
                mime="application/json"
            )
