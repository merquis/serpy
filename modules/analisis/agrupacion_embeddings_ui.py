# modules/analisis/agrupacion_embeddings_ui.py

import streamlit as st
import pandas as pd
from modules.analisis.agrupacion_embeddings_module import agrupar_titulos_por_embeddings

def render_agrupacion_embeddings():
    st.header("🔍 Agrupación Semántica de Etiquetas (H2/H3)")
    st.markdown("Genera clústeres de etiquetas semánticamente similares a partir de un JSON de scraping estructurado.")

    json_path = st.text_input("📁 Ruta al archivo JSON local", value="hotelesss.json")
    api_key = st.text_input("🔐 API Key de OpenAI", type="password")
    max_titulos = st.slider("🔢 Máximo de títulos a procesar", min_value=100, max_value=1000, value=500, step=100)
    n_clusters = st.slider("🧠 Número de clústeres", min_value=2, max_value=20, value=10)

    if st.button("🚀 Ejecutar agrupación"):
        if not json_path or not api_key:
            st.error("Debes ingresar tanto el JSON como la API Key.")
            return

        with st.spinner("Procesando embeddings y agrupando..."):
            try:
                df = agrupar_titulos_por_embeddings(
                    json_path=json_path,
                    api_key=api_key,
                    max_titulos=max_titulos,
                    n_clusters=n_clusters
                )
                st.success("✅ Agrupación completada")
                st.dataframe(df)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar CSV", data=csv, file_name="clusters_titulos.csv", mime="text/csv")
            except Exception as e:
                st.error(f"❌ Error al procesar: {e}")
