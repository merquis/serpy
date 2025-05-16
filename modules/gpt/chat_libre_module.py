# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI
import json

# Asegúrate de que estas importaciones sean correctas según tu estructura de proyecto
# y que las funciones hagan lo que esperas.
try:
    # Asumo que 'subir_json_a_drive' es tu función que usa la cuenta de servicio
    # y 'obtener_o_crear_subcarpeta' también.
    from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
    DRIVE_UTIL_LOADED = True
except ImportError:
    st.sidebar.error("Advertencia: Módulo de Drive no encontrado. Subida desactivada.")
    DRIVE_UTIL_LOADED = False
    def subir_json_a_drive(*args, **kwargs): return None
    def obtener_o_crear_subcarpeta(*args, **kwargs): return None

try:
    # Esta función ahora es responsable de la UI del file_uploader Y del procesamiento
    from modules.gpt.analizador_archivos_module import procesar_archivo_subido
    ANALIZADOR_LOADED = True
except ImportError:
    st.error("Advertencia: Módulo analizador de archivos no encontrado.")
    ANALIZADOR_LOADED = False
    def procesar_archivo_subido(): 
        st.error("Funcionalidad de subida de archivos no disponible.")
        return


def render_chat_libre():
    st.title("💬 Chat Libre Avanzado con GPT")
    st.markdown("Conversación con historial, carga de archivos para contexto y subida a Drive.")

    # --- Inicialización del Cliente OpenAI ---
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Revisa tus secrets.")
        return

    # --- Inicialización del Estado de Sesión ---
    if "chat_libre_history" not in st.session_state: # Renombrado para evitar colisiones
        st.session_state.chat_libre_history = []
    if "chat_libre_archivo_contexto" not in st.session_state: # Renombrado
        st.session_state.chat_libre_archivo_contexto = None
    
    # ID Proyecto Drive Global (debe ser establecido por streamlit_app.py o un selector global)
    # Usaremos st.session_state.id_proyecto_drive_seleccionado
    # Usaremos st.session_state.nombre_proyecto_seleccionado
    id_proyecto_drive_actual = st.session_state.get("id_proyecto_drive_seleccionado", None)
    nombre_proyecto_actual = st.session_state.get("nombre_proyecto_seleccionado", "General")


    # --- Barra Lateral para Configuraciones y Carga de Archivos ---
    with st.sidebar:
        st.markdown("### ⚙️ Configuración del Chat")

        # Mostrar proyecto activo
        if id_proyecto_drive_actual and nombre_proyecto_actual:
            st.success(f"Proyecto Activo: **{nombre_proyecto_actual}**")
        else:
            st.warning("⚠️ No hay proyecto de Drive activo globalmente. La subida a Drive estará deshabilitada.")

        # Selector de modelo
        modelos = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        modelo_seleccionado = st.selectbox(
            "🤖 Elige el modelo:", 
            modelos, 
            index=modelos.index(st.session_state.get("modelo_gpt_seleccionado", "gpt-4o")) if st.session_state.get("modelo_gpt_seleccionado", "gpt-4o") in modelos else 1, 
            key="chat_libre_modelo_selector_sidebar"
        )

        st.markdown("---")
        # Subida y análisis de archivos (la función procesar_archivo_subido maneja su propia UI de uploader)
        # Y actualiza st.session_state.archivo_contexto internamente (según tu código)
        # Lo renombro para que use el session_state específico de este chat.
        if ANALIZADOR_LOADED:
            # Modificamos procesar_archivo_subido para que tome una clave de session_state
            # o la función se modifica para usar 'chat_libre_archivo_contexto'
            # Por ahora, asumimos que la función procesar_archivo_subido en analizador_archivos_module.py
            # actualiza st.session_state.archivo_contexto. Lo ideal sería que
            # la función devuelva el contexto y lo asignemos aquí a la clave específica.
            # Para este ejemplo, mantendré tu lógica original de llamada:
            procesar_archivo_subido() # Esta función ahora debe actualizar 'st.session_state.chat_libre_archivo_contexto'
                                     # o devolver el contexto para que lo asignemos aquí.
                                     # Si procesar_archivo_subido usa st.session_state.archivo_contexto,
                                     # debemos copiar ese valor a nuestro session_state específico.
            if st.session_state.get("archivo_contexto"): # Clave usada por tu analizador
                st.session_state.chat_libre_archivo_contexto = st.session_state.archivo_contexto
                # Opcional: limpiar el st.session_state.archivo_contexto general para evitar fugas a otros módulos
                # del st.session_state.pop("archivo_contexto", None) 
        
        if st.session_state.get("chat_libre_archivo_contexto"):
            st.info("📄 Archivo(s) cargado(s) y en contexto.")
            if st.button("Quitar contexto de archivo", key="quitar_contexto_btn"):
                st.session_state.chat_libre_archivo_contexto = None
                # También podría ser útil limpiar st.session_state.archivo_contexto si es diferente
                if "archivo_contexto" in st.session_state:
                    del st.session_state["archivo_contexto"]
                st.rerun()


    # --- Mostrar Historial del Chat ---
    st.markdown("### 📝 Historial de Conversación")
    chat_container = st.container(height=450) # Un poco más de altura
    with chat_container:
        # Mostrar primero el contexto del archivo si existe, como un mensaje del sistema "invisible" para el usuario
        # pero presente para el modelo. Opcionalmente se podría mostrar algo al usuario.
        if st.session_state.get("chat_libre_archivo_contexto"):
            with st.chat_message("system", avatar="📄"): # Avatar opcional para el sistema
                 st.markdown("*Contexto del archivo cargado está siendo considerado por la IA.*")
                 # No es necesario mostrar todo el contexto aquí, ya se pasa a la API.

        for mensaje in st.session_state.chat_libre_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje['content'])

    # --- Entrada del Usuario ---
    if prompt := st.chat_input("Escribe tu mensaje aquí o pregunta sobre el archivo..."):
        st.session_state.chat_libre_history.append({"role": "user", "content": prompt})
        # Re-renderizar inmediatamente para mostrar el mensaje del usuario
        # No es necesario st.rerun() aquí, el widget de chat_input lo maneja.
        with chat_container: # Actualizar el contenedor directamente
            # Re-mostrar el mensaje de contexto si existe
            if st.session_state.get("chat_libre_archivo_contexto"):
                with st.chat_message("system", avatar="📄"):
                    st.markdown("*Contexto del archivo cargado está siendo considerado por la IA.*")
            # Re-mostrar todo el historial para que el nuevo mensaje aparezca al final
            for mensaje in st.session_state.chat_libre_history:
                 with st.chat_message(mensaje["role"]):
                    st.markdown(mensaje['content'])


        with st.spinner("GPT está escribiendo..."):
            try:
                mensajes_para_api = []
                # Añadir el contexto del archivo como primer mensaje del sistema si existe
                if st.session_state.get("chat_libre_archivo_contexto"):
                    mensajes_para_api.append({
                        "role": "system",
                        "content": st.session_state.chat_libre_archivo_contexto # Este es el prompt largo del analizador
                    })
                
                # Añadir el historial de chat normal
                for msg_hist in st.session_state.chat_libre_history:
                    mensajes_para_api.append({"role": msg_hist["role"], "content": msg_hist["content"]})
                
                response = client.chat.completions.create(
                    model=modelo_seleccionado,
                    messages=mensajes_para_api,
                    temperature=0.7,
                    max_tokens=2000, # Aumentado un poco por si el contexto es grande
                    stream=True
                )

                with chat_container: # Mostrar respuesta en el mismo contenedor
                    with st.chat_message("assistant"):
                        full_response_content = st.write_stream(response)
                
                st.session_state.chat_libre_history.append({"role": "assistant", "content": full_response_content})
                st.rerun() # Esencial después de write_stream y modificar session_state para actualizar la UI correctamente

            except Exception as e:
                st.error(f"❌ Error al contactar con OpenAI: {e}")
                error_msg = f"Error de API: {e}"
                st.session_state.chat_libre_history.append({"role": "assistant", "content": error_msg})
                # No es necesario un rerun aquí, el error se mostrará en la siguiente interacción o si se añade al chat
                with chat_container: # Mostrar error en el chat
                    with st.chat_message("assistant"):
                        st.error(error_msg)

    # --- Acciones Adicionales Debajo del Chat ---
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        # Descargar historial JSON
        contenido_json_descarga = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2) if st.session_state.chat_libre_history else ""
        st.download_button(
            label="💾 Descargar Historial",
            data=contenido_json_descarga,
            file_name=f"historial_chat_libre_{nombre_proyecto_actual.replace(' ','_')}.json",
            mime="application/json",
            key="chat_libre_descargar_json_btn",
            disabled=not st.session_state.chat_libre_history # Deshabilitar si no hay historial
        )

    with col_btn2:
        # Subir historial a Drive
        subir_drive_deshabilitado_btn = not id_proyecto_drive_actual or not st.session_state.chat_libre_history or not DRIVE_UTIL_LOADED
        if st.button("☁️ Subir a Drive", disabled=subir_drive_deshabilitado_btn, key="chat_libre_subir_drive_btn"):
            if id_proyecto_drive_actual and st.session_state.chat_libre_history: # Doble check
                historial_json_bytes_drive = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2).encode("utf-8")
                nombre_archivo_drive = f"Historial_ChatLibre_{nombre_proyecto_actual.replace(' ','_')}.json"
                
                # Usar la función importada de drive_utils
                # Asumimos que id_proyecto_drive_actual es el ID de la carpeta principal del proyecto
                # y queremos crear una subcarpeta "chat libre" dentro de ella.
                with st.spinner("Subiendo a Google Drive..."):
                    # Primero, obtener o crear la subcarpeta "chat libre"
                    id_subcarpeta_chat_libre = obtener_o_crear_subcarpeta( # Esta función debe existir en drive_utils
                        nombre_subcarpeta="chat libre", 
                        parent_id=id_proyecto_drive_actual
                    ) 
                
                    if id_subcarpeta_chat_libre:
                        enlace = subir_json_a_drive( # Esta es la función que sube el archivo
                            nombre_archivo=nombre_archivo_drive, 
                            contenido_bytes=historial_json_bytes_drive, 
                            carpeta_id=id_subcarpeta_chat_libre # Subir a la subcarpeta obtenida/creada
                        )
                        if enlace:
                            st.success(f"✅ Historial subido a Drive. [Ver archivo]({enlace})")
                        else:
                            st.error("❌ Error al subir el historial a Drive.")
                    else:
                        st.error("❌ No se pudo acceder o crear la subcarpeta 'chat libre' en Drive.")
            elif not id_proyecto_drive_actual:
                 st.warning("Selecciona un proyecto global para habilitar la subida a Drive.")
            elif not st.session_state.chat_libre_history:
                 st.info("El historial de chat está vacío.")


    with col_btn3:
        # Borrar historial y contexto de archivo
        def accion_borrar_todo():
            st.session_state.chat_libre_history = []
            st.session_state.chat_libre_archivo_contexto = None
            if "archivo_contexto" in st.session_state: # Limpiar el general también si se usa
                 del st.session_state["archivo_contexto"]
            st.success("🧼 Historial y contexto de archivo borrados.")
            # st.rerun() # on_click ya maneja el rerun implícitamente en muchos casos

        st.button(
            "🧹 Borrar Todo",
            type="primary",
            key="chat_libre_borrar_todo_btn",
            on_click=accion_borrar_todo,
            disabled=not st.session_state.chat_libre_history and not st.session_state.get("chat_libre_archivo_contexto")
        )
