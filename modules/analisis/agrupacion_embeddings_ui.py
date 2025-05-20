# modules/analisis/agrupacion_embeddings_ui.py
import streamlit as st
import json
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI

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
            st.success(f"✅ Archivo cargado desde el ordenador: {archivo.name}")
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
                st.success(f"✅ Archivo cargado desde Drive: {sel}")
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
        openai = OpenAI(api_key=api_key)

        def embed(text):
            try:
                return openai.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding
            except:
                return [0.0]*1536

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

                # === Asociación H3 a H2 por similitud de embeddings ===
                st.subheader("📎 Asociación automática de H3 bajo H2")
                with st.spinner("Calculando similitudes..."):
                    h2_summaries = []
                    h3_summaries = []

                    for i, grupo in df_h2.groupby("cluster"):
                        resumen = "; ".join(grupo["titulo"].tolist())
                        h2_summaries.append((i, resumen, embed(resumen)))

                    for j, grupo in df_h3.groupby("cluster"):
                        resumen = "; ".join(grupo["titulo"].tolist())
                        h3_summaries.append((j, resumen, embed(resumen)))

                    matrix_h2 = np.array([x[2] for x in h2_summaries])
                    matrix_h3 = np.array([x[2] for x in h3_summaries])
                    sim = cosine_similarity(matrix_h3, matrix_h2)

                    asociaciones = []
                    for idx_h3, fila in enumerate(sim):
                        h3_id, h3_text, _ = h3_summaries[idx_h3]
                        best_h2_idx = int(np.argmax(fila))
                        h2_id, h2_text, _ = h2_summaries[best_h2_idx]
                        asociaciones.append({
                            "h3_cluster": h3_id,
                            "h3_resumen": h3_text,
                            "h2_cluster": h2_id,
                            "h2_resumen": h2_text,
                            "similaridad": float(np.max(fila))
                        })

                    df_asoc = pd.DataFrame(asociaciones)

                # === Generar H1 maestro usando H1 reales y el árbol generado ===
                with open(source_id, "r", encoding="utf-8") as f:
                    contenido = json.load(f)
                busqueda = contenido[0].get("busqueda", "H1") if isinstance(contenido, list) else contenido.get("busqueda", "H1")

                h1_candidatos = []
                for entrada in contenido if isinstance(contenido, list) else [contenido]:
                    for res in entrada.get("resultados", []):
                        h1 = res.get("h1", {}).get("titulo")
                        if h1:
                            h1_candidatos.append(h1)

                resumen_arbol = "\n".join("- " + h2 + " → " + ", ".join(df_asoc[df_asoc.h2_resumen == h2].h3_resumen.tolist()) for h2 in df_asoc.h2_resumen.unique())

                prompt_h1 = f"""
Eres un consultor SEO experto. El usuario busca: "{busqueda}".
Estos son los títulos H1 de la competencia:
- """ + "\n- ".join(h1_candidatos[:10]) + f"""

Además, este es el esquema preliminar del artículo basado en las agrupaciones H2 → H3:
{resumen_arbol}

Genera un único título H1 para este artículo, que sea atractivo, claro, relevante, natural y muy optimizado para SEO.
"""
                try:
                    h1_ai = openai.chat.completions.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": prompt_h1}]
                    ).choices[0].message.content.strip()
                except:
                    h1_ai = busqueda

                estructura = {"title": h1_ai, "H2": []}
                for h2_id, h2_data in df_asoc.groupby("h2_cluster"):
                    h2_nombre = h2_data["h2_resumen"].iloc[0]
                    h3_nombres = h2_data["h3_resumen"].tolist()
                    estructura["H2"].append({"titulo": h2_nombre, "H3": h3_nombres})

                st.subheader("🌲 Estructura jerárquica sugerida (H1 → H2 → H3)")
                st.markdown(f"### 🏷️ H1 generado: {h1_ai}")
                st.json(estructura, expanded=True)

                st.download_button("⬇️ Descargar árbol JSON", data=json.dumps(estructura, ensure_ascii=False, indent=2), file_name="estructura_h1_h2_h3.json")

            except Exception as e:
                st.error(f"❌ Error al procesar: {e}")
