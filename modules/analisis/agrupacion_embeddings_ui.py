# modules/analisis/agrupacion_embeddings_ui.py
import streamlit as st
import json
from modules.analisis.agrupacion_embeddings_module import agrupar_titulos_por_embeddings
from modules.utils.drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive, obtener_o_crear_subcarpeta


def render_agrupacion_embeddings():
    st.title("🔍 Agrupación semántica y árbol SEO")
    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador"], horizontal=True)

    source = None
    source_id = None

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("Sube un archivo JSON", type="json")
        if archivo:
            source = "local"
            source_id = f"/tmp/{archivo.name}"
            with open(source_id, "wb") as f:
                f.write(archivo.read())
            st.success(f"✅ Archivo cargado: {archivo.name}")

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.warning("⚠️ Debes seleccionar un proyecto en la barra lateral")
            return

        carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta)
        if archivos:
            archivo_seleccionado = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                source = "drive"
                source_id = archivos[archivo_seleccionado]
                st.success(f"✅ Archivo cargado desde Drive: {archivo_seleccionado}")
        else:
            st.info("No se encontraron archivos en la carpeta del proyecto")

    st.markdown("---")
    n_clusters = st.slider("Número de clústeres por nivel", 2, 30, 10)
    max_titulos = st.slider("Máximo de títulos por nivel", 100, 1500, 500, step=50)

    if st.button("🚀 Ejecutar análisis SEO"):
        if not source or not source_id:
            st.error("❌ Debes cargar un archivo antes de continuar")
            return

        api_key = st.secrets["openai"]["api_key"]
        with st.spinner("Procesando agrupaciones y generando estructura SEO..."):
            estructura = agrupar_titulos_por_embeddings(
                api_key=api_key,
                source=source,
                source_id=source_id,
                max_titulos=max_titulos,
                n_clusters=n_clusters
            )

        st.markdown(f"### 🏷️ H1 generado: `{estructura['title']}`")
        st.subheader("🌳 Árbol H1 → H2 → H3")
        st.json(estructura, expanded=True)

        st.download_button(
            "⬇️ Descargar JSON SEO",
            data=json.dumps(estructura, indent=2, ensure_ascii=False),
            file_name="estructura_seo.json",
            mime="application/json"
        )
