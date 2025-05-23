# scraping_etiquetas_url.py (VERSÍON CORREGIDA)

import json
import streamlit as st
import asyncio
import logging

# --- IMPORTACIONES DE TU PROYECTO ---
# 👇👇👇 ¡¡¡AHORA IMPORTAMOS LA CLASE Y ASUMIMOS MONGO!!! 👇👇👇
try:
    # Importamos la CLASE desde drive_service.py
    from services.drive_service import DriveService
    # Asumimos que 'subir_a_mongodb' está en 'mongo_service.py'. ¡AJUSTA SI ES NECESARIO!
    from services.mongo_service import subir_a_mongodb
    from services.tag_scraping_service import TagScrapingService # Importamos el servicio de scraping

except ImportError as e:
    st.error(f"❌ Error de Importación: {e}. "
             f"Verifica que 'services/drive_service.py' define la clase 'DriveService' y "
             f"que 'services/mongo_service.py' existe y define 'subir_a_mongodb'.")
    st.stop()
# --- FIN IMPORTACIONES ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def render_scraping_etiquetas_url():
    """Renderiza la página de Streamlit para el scraping de etiquetas."""

    st.session_state["_called_script"] = "scraping_etiquetas_url"
    st.title("🧬 Extraer estructura jerárquica (h1 → h2 → h3)")
    st.markdown("### 📁 Sube o selecciona un archivo JSON con URLs")

    # 👇👇👇 Creamos UNA instancia del servicio de Drive 👇👇👇
    try:
        drive_service = DriveService()
    except Exception as e:
        st.error(f"❌ Error al inicializar DriveService: {e}. ¿Están bien configurados los secretos?")
        st.stop()

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador"], horizontal=True, index=0)

    def procesar_json(crudo):
        """Intenta parsear el contenido JSON."""
        try:
            return json.loads(crudo.decode("utf-8") if isinstance(crudo, bytes) else crudo)
        except Exception as e: st.error(f"❌ Error al procesar JSON: {e}"); return None

    # --- Lógica para cargar JSON ---
    if fuente == "Desde ordenador":
        archivo_subido = st.file_uploader("Sube archivo JSON", type="json")
        if archivo_subido:
            st.session_state["json_contenido"] = archivo_subido.read()
            st.session_state["json_nombre"] = archivo_subido.name
            st.session_state.pop("salida_json", None)
    else: # Desde Drive
        if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
            st.error("❌ Selecciona primero un proyecto en la barra lateral izquierda.")
            return

        try:
            carpeta_principal = st.session_state.proyecto_id
            # 👇👇👇 Usamos los MÉTODOS del objeto drive_service 👇👇👇
            subcarpeta_id = drive_service.get_or_create_folder("scraper urls google", carpeta_principal)
            archivos_json = drive_service.list_json_files_in_folder(subcarpeta_id)

            if not archivos_json:
                st.warning("⚠️ No hay archivos JSON en la subcarpeta 'scraper urls google'.")
                return

            archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
            if st.button("📅 Cargar archivo de Drive"):
                # 👇👇👇 Usamos el MÉTODO del objeto drive_service 👇👇👇
                st.session_state["json_contenido"] = drive_service.get_file_content(archivos_json[archivo_drive])
                st.session_state["json_nombre"] = archivo_drive
                st.session_state.pop("salida_json", None)
        except Exception as e:
            st.error(f"❌ Error interactuando con Google Drive: {e}")
            return

    # --- Lógica Principal de Procesamiento ---
    if "json_contenido" in st.session_state and "salida_json" not in st.session_state:
        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json: return

        max_concurrentes = st.slider("🔁 Concurrencia máxima", 1, 10, 5)
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_progress(message: str, percentage: float):
            status_text.text(message)
            progress_bar.progress(percentage)

        st.info("🚀 Iniciando proceso de scraping...")
        try:
            service = TagScrapingService()
            salidas = asyncio.run(service.scrape_tags_from_json(datos_json, max_concurrentes, update_progress))
            status_text.success("✅ ¡Proceso completado!")
            st.session_state["salida_json"] = salidas
            base = st.session_state.get("json_nombre", "etiquetas.json")
            st.session_state["nombre_archivo_exportar"] = base.replace(".json", "_ALL.json")
        except Exception as e:
            st.error(f"❌ Ocurrió un error general durante el procesamiento: {e}")
            st.session_state.pop("salida_json", None)

    # --- Lógica de Exportación y Visualización ---
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
            if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
                if st.button("☁️ Subir archivo a Google Drive"):
                    try:
                        contenido_bytes = json.dumps(salida, ensure_ascii=False, indent=2).encode("utf-8")
                        # 👇👇👇 Usamos el MÉTODO del objeto drive_service 👇👇👇
                        enlace = drive_service.upload_file(nombre_archivo, contenido_bytes, st.session_state["proyecto_id"])
                        if enlace: st.success(f"✅ Subido: [Ver en Drive]({enlace})")
                        else: st.error("❌ Error al subir archivo a Drive.")
                    except Exception as e: st.error(f"❌ Error al subir a Drive: {e}")
            else: st.warning("Selecciona un proyecto para subir a Drive.")

        with col_export[2]:
            if "mongodb" in st.secrets and "db" in st.secrets["mongodb"] and "uri" in st.secrets["mongodb"]:
                if st.button("📤 Subir JSON a MongoDB"):
                    try:
                        inserted_id = subir_a_mongodb( # <-- Asegúrate de que 'subir_a_mongodb' existe y se importa bien
                            salida,
                            db_name=st.secrets["mongodb"]["db"],
                            collection_name="hoteles",
                            uri=st.secrets["mongodb"]["uri"]
                        )
                        st.success(f"✅ Datos subidos a MongoDB.")
                    except Exception as e: st.error(f"❌ Error al subir a MongoDB: {e}")
            else: st.warning("Configura los secretos de MongoDB para subir.")

        st.subheader("📦 Resultados estructurados")
        st.json(salida, expanded=True)

# Llama a tu función principal si es necesario
# render_scraping_etiquetas_url()
