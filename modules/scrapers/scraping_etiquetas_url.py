import json
import streamlit as st
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)
from modules.utils.scraper_tags_tree import scrape_tags_as_tree
from modules.utils.mongo_utils import subir_a_mongodb

def render_scraping_etiquetas_url():
    st.session_state["_called_script"] = "scraping_etiquetas_url"
    st.title("🧬 Extraer estructura jerárquica (h1 → h2 → h3) desde archivo JSON")
    st.markdown("### 📁 Sube un archivo JSON con URLs obtenidas de Google")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador"], horizontal=True, index=0)

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
            st.session_state.pop("salida_json", None)

    else:
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral izquierda.")
            return

        carpeta_principal = st.session_state.proyecto_id
        subcarpeta_id = obtener_o_crear_subcarpeta("scraper urls google", carpeta_principal)
        if not subcarpeta_id:
            st.error("❌ No se pudo acceder a la subcarpeta scraper urls google.")
            return

        archivos_json = listar_archivos_en_carpeta(subcarpeta_id)
        if not archivos_json:
            st.warning("⚠️ No hay archivos JSON en esta subcarpeta del proyecto.")
            return

        archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
        if st.button("📅 Cargar archivo de Drive"):
            st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos_json[archivo_drive])
            st.session_state["json_nombre"] = archivo_drive
            st.session_state.pop("salida_json", None)

    if "json_contenido" in st.session_state and "salida_json" not in st.session_state:
        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json:
            return

        iterable = datos_json if isinstance(datos_json, list) else [datos_json]
        primer = iterable[0]

        contexto = {
            "busqueda": primer.get("busqueda", ""),
            "idioma": primer.get("idioma", ""),
            "region": primer.get("region", ""),
            "dominio": primer.get("dominio", ""),
            "url_busqueda": primer.get("url_busqueda", "")
        }

        todas_urls = []
        for entrada in iterable:
            if isinstance(entrada, dict) and "urls" in entrada:
                for item in entrada["urls"]:
                    if isinstance(item, str):
                        todas_urls.append(item)
                    elif isinstance(item, dict) and "url" in item:
                        todas_urls.append(item["url"])
            if isinstance(entrada, dict) and "resultados" in entrada:
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
                resultado = scrape_tags_as_tree(url)
                resultados.append(resultado)

        st.session_state["salida_json"] = {**contexto, "resultados": resultados}
        base = st.session_state.get("json_nombre", "etiquetas_jerarquicas.json")
        st.session_state["nombre_archivo_exportar"] = base.replace(".json", "_ALL.json") if base.endswith(".json") else base + "_ALL.json"

    if "salida_json" in st.session_state:
        salida = st.session_state["salida_json"]
        nombre_archivo = st.text_input("📄 Nombre para exportar el archivo JSON", value=st.session_state["nombre_archivo_exportar"])
        st.session_state["nombre_archivo_exportar"] = nombre_archivo

        col_export = st.columns([1, 1, 1])

        with col_export[0]:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=json.dumps(salida, ensure_ascii=False, indent=2),
                file_name=nombre_archivo,
                mime="application/json"
            )

        with col_export[1]:
            if st.button("☁️ Subir archivo a Google Drive", key="subir_drive"):
                contenido_bytes = json.dumps(salida, ensure_ascii=False, indent=2).encode("utf-8")
                enlace = subir_json_a_drive(nombre_archivo, contenido_bytes, st.session_state["proyecto_id"])
                if enlace:
                    st.success(f"✅ Subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir archivo a Drive.")

        with col_export[2]:
            if st.button("📤 Subir JSON a MongoDB", key="subir_mongo"):
                try:
                    inserted_id = subir_a_mongodb(
                        salida,
                        db_name = st.secrets["mongodb"]["db"],  # Base de datos actualizada
                        collection_name="hoteles",  # Colección actualizada
                        uri = st.secrets["mongodb"]["uri"]
                    )
                    st.success(f"✅ Subido a MongoDB con ID: `{inserted_id}`")
                except Exception as e:
                    st.error(f"❌ Error al subir a MongoDB: {e}")

        st.subheader("📦 Resultados estructurados")
        st.markdown("<div style='max-width: 100%; overflow-x: auto;'>", unsafe_allow_html=True)
        st.json(salida)
        st.markdown("</div>", unsafe_allow_html=True)
