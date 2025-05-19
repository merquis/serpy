# modules/analisis/agrupacion_embeddings_ui.py
import streamlit as st
import json
import pandas as pd
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    obtener_o_crear_subcarpeta
)

from modules.analisis.agrupacion_embeddings_module import agrupar_titulos_por_embeddings

def render_agrupacion_embeddings():
    st.title("🔍 Agrupación Semántica de Etiquetas (H2/H3)")
    st.markdown("Genera clústeres de etiquetas semánticamente similares a partir de un JSON de scraping estructurado.")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador"], horizontal=True)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            source = "local"
            source_id = f"/tmp/{archivo.name}"
            with open(source_id, "wb") as f:
                f.write(archivo.read())
            st.session_state["agrupacion_source"] = source
            st.session_state["agrupacion_source_id"] = source_id

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.warning("⚠️ Selecciona primero un proyecto en la barra lateral.")
            return

        carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta)
        if archivos:
            sel = st.selectbox("Archivo en Drive:", list(archivos.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos[sel])
                st.session_state["json_nombre"] = sel
                st.session_state["agrupacion_source"] = "drive"
                st.session_state["agrupacion_source_id"] = archivos[sel]
        else:
            st.info("No hay archivos JSON disponibles en esta carpeta de Drive.")

    st.markdown("### ⚙️ Parámetros")

    max_titulos = st.slider("🔢 Títulos a procesar", min_value=150, max_value=1500, value=500, step=50)
    n_clusters = st.slider("🧠 Número de clústeres", min_value=2, max_value=30, value=10)

    if st.button("🚀 Ejecutar agrupación"):
        source = st.session_state.get("agrupacion_source")
        source_id = st.session_state.get("agrupacion_source_id")

        if not (source and source_id):
            st.error("⚠️ Debes cargar un archivo JSON válido desde ordenador o Drive.")
            return

        api_key = st.secrets["openai"]["api_key"]
        with st.spinner("Procesando embeddings y agrupando..."):
            try:
                df_h2, df_h3 = agrupar_titulos_por_embeddings(
                    api_key=api_key,
                    source=source,
                    source_id=source_id,
                    max_titulos=max_titulos,
                    n_clusters=n_clusters
                )
                st.success("✅ Agrupación completada")

                st.subheader("Agrupación de H2")
                st.dataframe(df_h2)
                csv_h2 = df_h2.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar H2 CSV", data=csv_h2, file_name="clusters_h2.csv", mime="text/csv")

                st.subheader("Agrupación de H3")
                st.dataframe(df_h3)
                csv_h3 = df_h3.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar H3 CSV", data=csv_h3, file_name="clusters_h3.csv", mime="text/csv")

            except Exception as e:
                st.error(f"❌ Error al procesar: {e}")
