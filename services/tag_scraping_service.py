# scraping_etiquetas_url.py (o el nombre de tu archivo Streamlit)

import json
import streamlit as st
import asyncio
import logging

# --- IMPORTACIONES DE TU PROYECTO ---
# 👇👇👇 ¡¡¡ASEGÚRATE DE QUE ESTAS RUTAS SON CORRECTAS!!! 👇👇👇
# Asumimos que tus funciones están ahora en 'services/drive_service.py'
# y 'services/mongo_service.py'. ¡AJUSTA SI ES NECESARIO!
try:
    from services.drive_service import (
        listar_archivos_en_carpeta,
        obtener_contenido_archivo_drive,
        subir_json_a_drive,
        obtener_o_crear_subcarpeta
    )
    # Asumimos que 'subir_a_mongodb' está en 'mongo_service.py'. ¡AJUSTA SI ES NECESARIO!
    from services.mongo_service import subir_a_mongodb
    from services.tag_scraping_service import TagScrapingService # Importamos el servicio

except ImportError as e:
    st.error(f"❌ Error de Importación: {e}. "
             f"Verifica la estructura de tu proyecto y los nombres de los archivos en 'services'. "
             "Asegúrate de que existan 'drive_service.py' y 'mongo_service.py' "
             "con las funciones necesarias, o ajusta las importaciones aquí.")
    # Detenemos la ejecución si las importaciones fallan
    st.stop()
# --- FIN IMPORTACIONES ---

# Configurar logging básico para ver info del servicio en la consola
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def render_scraping_etiquetas_url():
    """Renderiza la página de Streamlit para el scraping de etiquetas."""

    st.session_state["_called_script"] = "scraping_etiquetas_url"
    st.title("🧬 Extraer estructura jerárquica (h1 → h2 → h3)")
    st.markdown("### 📁 Sube o selecciona un archivo JSON con URLs")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde Drive", "Desde ordenador"], horizontal=True, index=0)

    def procesar_json(crudo):
        """Intenta parsear el contenido JSON."""
        try:
            if isinstance(crudo, bytes):
                crudo = crudo.decode("utf-8")
            return json.loads(crudo)
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo JSON: {e}")
            return None

    # --- Lógica para cargar JSON (Desde Drive o Local) ---
    if fuente == "Desde ordenador":
        archivo_subido = st.file_uploader("Sube archivo JSON", type="json")
        if archivo_subido:
            st.session_state["json_contenido"] = archivo_subido.read()
            st.session_state["json_nombre"] = archivo_subido.name
            st.session_state.pop("salida_json", None) # Limpia salida anterior
    else: # Desde Drive
        if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
            st.error("❌ Selecciona primero un proyecto en la barra lateral izquierda.")
            return

        try:
            carpeta_principal = st.session_state.proyecto_id
            # Asumiendo que 'obtener_o_crear_subcarpeta' y 'listar_archivos_en_carpeta'
            # vienen de 'drive_service.py'
            subcarpeta_id = obtener_o_crear_subcarpeta("scraper urls google", carpeta_principal)
            if not subcarpeta_id:
                st.error("❌ No se pudo acceder a la subcarpeta 'scraper urls google'.")
                return

            archivos_json = listar_archivos_en_carpeta(subcarpeta_id)
            if not archivos_json:
                st.warning("⚠️ No hay archivos JSON en la subcarpeta 'scraper urls google'.")
                return

            archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
            if st.button("📅 Cargar archivo de Drive"):
                st.session_state["json_contenido"] = obtener_contenido_archivo_drive(archivos_json[archivo_drive])
                st.session_state["json_nombre"] = archivo_drive
                st.session_state.pop("salida_json", None) # Limpia salida anterior
        except Exception as e:
            st.error(f"❌ Error interactuando con Google Drive: {e}")
            return

    # --- Lógica Principal de Procesamiento ---
    if "json_contenido" in st.session_state and "salida_json" not in st.session_state:
        datos_json = procesar_json(st.session_state["json_contenido"])
        if not datos_json: return # Si hay error en JSON, no continuamos

        max_concurrentes = st.slider("🔁 Concurrencia máxima", min_value=1, max_value=10, value=5)

        # Contenedores para el progreso en Streamlit
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        # 👇👇👇 FUNCIÓN DE CALLBACK CORREGIDA (ACEPTA 2 ARGUMENTOS) 👇👇👇
        def update_progress(message: str, percentage: float):
            """Callback para actualizar la UI de Streamlit."""
            status_text.text(message)
            progress_bar.progress(percentage)

        st.info("🚀 Iniciando proceso de scraping... Esto puede tardar varios minutos.")

        try:
            # Instancia y ejecuta el servicio
            service = TagScrapingService()
            # Usamos asyncio.run para ejecutar nuestra función async principal
            salidas = asyncio.run(service.scrape_tags_from_json(
                datos_json,
                max_concurrentes,
                update_progress # Pasa la función de callback
            ))

            status_text.success("✅ ¡Proceso completado!")
            st.session_state["salida_json"] = salidas
            base = st.session_state.get("json_nombre", "etiquetas_jerarquicas.json")
            st.session_state["nombre_archivo_exportar"] = (
                base.replace(".json", "_ALL.json") if base.endswith(".json") else base + "_ALL.json"
            )

        except Exception as e:
            st.error(f"❌ Ocurrió un error general durante el procesamiento: {e}")
            # Limpiamos para poder reintentar si es necesario
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
                        enlace = subir_json_a_drive(nombre_archivo, contenido_bytes, st.session_state["proyecto_id"])
                        if enlace:
                            st.success(f"✅ Subido: [Ver en Drive]({enlace})")
                        else:
                            st.error("❌ Error al subir archivo a Drive.")
                    except Exception as e:
                        st.error(f"❌ Error al subir a Drive: {e}")
            else:
                st.warning("Selecciona un proyecto para subir a Drive.")

        with col_export[2]:
            # Comprueba si los secretos de MongoDB están configurados
            if "mongodb" in st.secrets and "db" in st.secrets["mongodb"] and "uri" in st.secrets["mongodb"]:
                if st.button("📤 Subir JSON a MongoDB"):
                    try:
                        inserted_id = subir_a_mongodb(
                            salida,
                            db_name=st.secrets["mongodb"]["db"],
                            collection_name="hoteles", # O hazlo configurable
                            uri=st.secrets["mongodb"]["uri"]
                        )
                        st.success(f"✅ Datos subidos a MongoDB.")
                    except Exception as e:
                        st.error(f"❌ Error al subir a MongoDB: {e}")
            else:
                st.warning("Configura los secretos de MongoDB para subir.")


        st.subheader("📦 Resultados estructurados")
        # 👇👇👇 CORRECCIÓN: Usamos expanded=True 👇👇👇
        st.json(salida, expanded=True)

# --- Punto de entrada ---
# Llama a la función principal para renderizar la página.
# Asegúrate de que esto se llama correctamente en tu app multipágina si la tienes.
# Si es una app de una sola página, simplemente puedes llamarla al final.
# render_scraping_etiquetas_url()
