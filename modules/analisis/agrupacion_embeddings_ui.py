# modules/analisis/agrupacion_embeddings_ui.py
import streamlit as st
import json
from openai import OpenAI
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    obtener_o_crear_subcarpeta
)
from modules.utils.mongo_utils import obtener_documentos_mongodb
from modules.analisis.agrupacion_embeddings_module import agrupar_titulos_por_embeddings

def render_agrupacion_embeddings():
    st.title("🔍 Agrupación semántica y árbol SEO")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador", "Desde MongoDB"], horizontal=True)

    source = source_id = None

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.json_contenido = archivo.read()
            st.session_state.source = "local"
            st.session_state.source_id = f"/tmp/{archivo.name}"
            with open(st.session_state.source_id, "wb") as f:
                f.write(st.session_state.json_contenido)
            st.success("✅ Archivo cargado desde el ordenador")

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.warning("⚠️ Selecciona primero un proyecto en la barra lateral.")
            return
        carpeta = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta)
        if archivos:
            sel = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
            if st.button("📂 Cargar archivo de Drive"):
                st.session_state.json_contenido = obtener_contenido_archivo_drive(archivos[sel])
                st.session_state.source = "drive"
                st.session_state.source_id = st.session_state.json_contenido
                st.success("✅ Archivo cargado desde Drive")
        else:
            st.warning("⚠️ No hay archivos en esa carpeta")

    elif fuente == "Desde MongoDB":
        docs = obtener_documentos_mongodb(
            uri=st.secrets["mongodb"]["uri"],
            db_name=st.secrets["mongodb"]["db"],
            collection_name="hoteles",
            campo_nombre="busqueda"
        )
        if docs:
            sel = st.selectbox("Selecciona búsqueda:", docs)
            if st.button("📂 Cargar desde MongoDB"):
                st.session_state.source = "mongo"
                st.session_state.source_id = sel
                st.success(f"✅ Documento MongoDB cargado: {sel}")
        else:
            st.warning("⚠️ No hay documentos en MongoDB")

    # === Parámetros ===
    st.markdown("""---
    ### ⚙️ Parámetros de Agrupación
    """)
    col1, col2 = st.columns(2)
    with col1:
        n_clusters_h2 = st.slider("🧠 Número de clústeres para H2", 2, 30, 10)
        max_titulos_h2 = st.slider("📄 Máximo de títulos H2", 100, 1500, 300)
    with col2:
        n_clusters_h3 = st.slider("🧠 Número de clústeres para H3", 2, 100, 30)
        max_titulos_h3 = st.slider("📄 Máximo de títulos H3", 100, 3000, 900)

    if st.button("🚀 Ejecutar análisis SEO"):
        if "source" not in st.session_state or "source_id" not in st.session_state:
            st.error("❌ Debes cargar un archivo antes de continuar")
            return

        with st.spinner("Analizando y generando estructura SEO..."):
            try:
                estructura = agrupar_titulos_por_embeddings(
                    api_key=st.secrets["openai"]["api_key"],
                    source=st.session_state.source,
                    source_id=st.session_state.source_id,
                    max_titulos_h2=max_titulos_h2,
                    max_titulos_h3=max_titulos_h3,
                    n_clusters_h2=n_clusters_h2,
                    n_clusters_h3=n_clusters_h3,
                    mongo_uri=st.secrets["mongodb"]["uri"],
                    mongo_db=st.secrets["mongodb"]["db"]
                )
                st.success("✅ Árbol SEO generado")
                st.markdown(f"### 🏷️ H1 generado: `{estructura['title']}`")
                st.json(estructura, expanded=True)
                st.download_button("⬇️ Descargar JSON", data=json.dumps(estructura, ensure_ascii=False, indent=2),
                                   file_name="arbol_seo.json")
            except Exception as e:
                st.error(f"❌ Error durante el análisis: {e}")
