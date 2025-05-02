# scraping_etiquetas_url.py
import json
import streamlit as st
from drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive
from bs4 import BeautifulSoup
import requests

# ════════════════════════════════════════════════
# 🎯 MÓDULO: Scraping de etiquetas desde archivo JSON
# ════════════════════════════════════════════════

def render_scraping_etiquetas_url():
    st.title("🧬 Scraping de URLs desde archivo JSON")
    st.markdown("### 📁 Sube un archivo JSON con URLs obtenidas de Google")

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
            st.error("❌ Selecciona primero un proyecto en la barra lateral izquierda.")
            return

        carpeta_id = st.session_state.proyecto_id
        archivos_json = listar_archivos_en_carpeta(carpeta_id)

        if archivos_json:
            archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos_json[archivo_drive])
                st.session_state["json_nombre"] = archivo_drive
        else:
            st.warning("⚠️ No hay archivos JSON en este proyecto.")
            return

    if "json_contenido" in st.session_state:
        st.success(f"✅ Archivo cargado: {st.session_state['json_nombre']}")

        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json:
            return

        # Extraer URLs
        todas_urls = []
        for entrada in datos_json:
            urls = entrada.get("urls", [])
            if isinstance(urls, list):
                for item in urls:
                    if isinstance(item, str):
                        todas_urls.append(item)
                    elif isinstance(item, dict):
                        url = item.get("url")
                        if url:
                            todas_urls.append(url)

        if not todas_urls:
            st.warning("⚠️ No se encontraron URLs en el archivo JSON.")
            return

        # Selección de etiquetas
        st.markdown("### 🏷️ Etiquetas a extraer")
        etiquetas = []
        col1, col2, col3, col4 = st.columns(4)
        with col1: title_check = st.checkbox("title")
        with col2: h1_check = st.checkbox("H1")
        with col3: h2_check = st.checkbox("H2")
        with col4: h3_check = st.checkbox("H3")

        if title_check: etiquetas.append("title")
        if h1_check: etiquetas.append("h1")
        if h2_check: etiquetas.append("h2")
        if h3_check: etiquetas.append("h3")

        if not etiquetas:
            st.info("ℹ️ Selecciona al
