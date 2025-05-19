import streamlit as st
import json
import pandas as pd
from modules.analisis.agrupacion_embeddings_module import agrupar_titulos_por_embeddings
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    obtener_o_crear_subcarpeta
)


def render_agrupacion_embeddings():
    st.title("🔍 Agrupación Semántica de Etiquetas (H2/H3)")
    st.markdown("Genera clústeres de etiquetas semánticamente similares a partir de un JSON de scraping estructurado.")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador"], horizontal=True)

    source = None
    source_id = None
    json_data = None

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            source = "local"
            source_id = f"/tmp/{archivo.name}"
            with open(source_id, "wb") as f:
                f.write(archivo.read())

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.warning("⚠️ Selecciona primero un proyecto en la barra lateral.")
            return

        carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta)
        if archivos:
            sel = st.selectbox("Archivo en Drive:", list(archivos.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                st.session_state.json_contenido = obtener_contenido_archivo_drive(archivos[sel])
                st.session_state.json_nombre = sel
                source = "drive"
                source_id = archivos[sel]
        else:
            st.info("No hay archivos JSON disponibles en esta carpeta de Drive.")

    max_titulos = st.slider("🔢 Máximo de títulos a procesar", min_value=100, max_value=1000, value=500, step=100)
    n_clusters = st.slider("🧠 Número de clústeres", min_value=2, max_value=20, value=10)

    if st.button("🚀 Ejecutar agrupación"):
        if not (source and source_id):
            st.error("⚠️ Debes cargar un archivo JSON válido desde ordenador o Drive.")
            return

        api_key = st.secrets["openai"]["api_key"]
        with st.spinner("Procesando embeddings y agrupando..."):
            try:
                df = agrupar_titulos_por_embeddings(
                    api_key=api_key,
                    source=source,
                    source_id=source_id,
                    max_titulos=max_titulos,
                    n_clusters=n_clusters
                )
                st.success("✅ Agrupación completada")
                st.dataframe(df)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar CSV", data=csv, file_name="clusters_titulos.csv", mime="text/csv")

            except Exception as e:
                st.error(f"❌ Error al procesar: {e}")
