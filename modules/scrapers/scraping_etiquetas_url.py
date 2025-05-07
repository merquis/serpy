import json
import streamlit as st
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_archivo_a_drive
)
from modules.utils.scraper_tags_tree import scrape_tags_as_tree

def render_scraping_etiquetas_url():
    st.title("🧬 Extraer estructura jerárquica (h1 → h2 → h3) desde archivo JSON")
    st.markdown("### 📁 Sube un archivo JSON con URLs obtenidas de Google")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde ordenador", "Desde Drive"], horizontal=True)

    # ── Helper para convertir bytes → dict ----------------------------------
    def procesar_json(crudo):
        try:
            if isinstance(crudo, bytes):
                crudo = crudo.decode("utf-8")
            return json.loads(crudo)
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")
            return None

    # ── Subida o carga desde Drive -----------------------------------------
    if fuente == "Desde ordenador":
        archivo_subido = st.file_uploader("Sube archivo JSON", type="json")
        if archivo_subido:
            st.session_state["json_contenido"] = archivo_subido.read()
            st.session_state["json_nombre"]   = archivo_subido.name

    else:  # Desde Drive
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral izquierda.")
            return

        carpeta_id = st.session_state.proyecto_id
        archivos_json = listar_archivos_en_carpeta(carpeta_id)

        if archivos_json:
            archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos_json[archivo_drive])
                st.session_state["json_nombre"]    = archivo_drive
        else:
            st.warning("⚠️ No hay archivos JSON en este proyecto.")
            return

    # ── Procesar el JSON ----------------------------------------------------
    if "json_contenido" in st.session_state:
        st.success(f"✅ Archivo cargado: {st.session_state['json_nombre']}")

        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json:
            return

        # Puede ser lista o dict
        iterable = datos_json if isinstance(datos_json, list) else [datos_json]
        primer    = iterable[0]

        contexto = {
            "busqueda":     primer.get("busqueda", ""),
            "idioma":       primer.get("idioma",   ""),
            "region":       primer.get("region",   ""),
            "dominio":      primer.get("dominio",  ""),
            "url_busqueda": primer.get("url_busqueda", "")
        }

        # ── Extraer URLs en ambos formatos ---------------------------------
        todas_urls = []
        for entrada in iterable:
            # Formato clásico: "urls": [...]
            if isinstance(entrada, dict) and "urls" in entrada and isinstance(entrada["urls"], list):
                for item in entrada["urls"]:
                    if isinstance(item, str):
                        todas_urls.append(item)
                    elif isinstance(item, dict) and "url" in item:
                        todas_urls.append(item["url"])

            # Formato nuevo: "resultados": [ {"url": ...} ]
            if isinstance(entrada, dict) and "resultados" in entrada and isinstance(entrada["resultados"], list):
                for res in entrada["resultados"]:
                    if isinstance(res, dict) and "url" in res:
                        todas_urls.append(res["url"])

        if not todas_urls:
            st.warning("⚠️ No se encontraron URLs válidas en el archivo.")
            return

        st.info(f"🔍 Procesando {len(todas_urls)} URLs...")

        resultados = []
        for url in todas_urls:
            with st.spinner(f"Analizando {url}..."):
                resultados.append(scrape_tags_as_tree(url))

        salida = {**contexto, "resultados": resultados}

        st.subheader("📦 Resultados estructurados")
        st.json(salida)

        st.markdown("---")
        col1, col2 = st.columns([2, 2])

        with col1:
            nombre_archivo = st.text_input(
                "📄 Nombre para exportar el archivo JSON",
                value="etiquetas_jerarquicas.json"
            )
            if st.button("💾 Exportar JSON"):
                st.download_button(
                    label="⬇️ Descargar archivo JSON",
                    data=json.dumps(salida, ensure_ascii=False, indent=2),
                    file_name=nombre_archivo,
                    mime="application/json"
                )

        with col2:
            if st.button("☁️ Subir archivo a Google Drive"):
                if "proyecto_id" not in st.session_state:
                    st.error("❌ No se ha seleccionado un proyecto.")
                else:
                    subir_archivo_a_drive(
                        contenido=json.dumps(salida, ensure_ascii=False, indent=2),
                        nombre_archivo=nombre_archivo,
                        carpeta_id=st.session_state.proyecto_id
                    )
                    st.success(f"✅ Archivo '{nombre_archivo}' subido correctamente a Google Drive.")
