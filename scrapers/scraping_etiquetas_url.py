# scraping_etiquetas_url.py

import json
import streamlit as st
from drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive
from scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url, extraer_urls_de_json

# ════════════════════════════════════════════════
# 🧬 Extraer etiquetas desde archivo JSON
# ════════════════════════════════════════════════
def render_scraping_etiquetas_url():
    st.title("🧬 Extraer etiquetas SEO desde archivo JSON")
    st.markdown("Sube un archivo JSON con URLs o selecciona uno desde Drive")

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
        archivo_subido = st.file_uploader("📁 Sube archivo JSON", type="json")
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
            archivo_drive = st.selectbox("📂 Selecciona un archivo de Drive", list(archivos_json.keys()))
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

        urls = extraer_urls_de_json(datos_json)
        if not urls:
            st.warning("⚠️ No se encontraron URLs válidas en el archivo.")
            return

        etiquetas = seleccionar_etiquetas_html()
        if not etiquetas:
            st.info("ℹ️ Selecciona al menos una etiqueta para extraer.")
            return

        if st.button("🔍 Extraer etiquetas"):
            resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]

            st.subheader("📦 Resultados obtenidos")
            st.json(resultados)

            nombre_salida = "etiquetas_extraidas.json"
            st.download_button(
                label="⬇️ Descargar JSON",
                data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name=nombre_salida,
                mime="application/json"
            )
