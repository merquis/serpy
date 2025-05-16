# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI
import json
import logging # Para mejor depuración

logger = logging.getLogger(__name__)

# --- IMPORTACIÓN REAL DE LA FUNCIÓN DE DRIVE ---
try:
    from modules.utils.drive_utils import subir_json_a_drive_especifico
    DRIVE_UTIL_LOADED = True
except ImportError as e:
    logger.error(f"Fallo al importar 'subir_json_a_drive_especifico': {e}", exc_info=True)
    st.sidebar.error("Error crítico: Módulo de utilidades de Drive no encontrado. La subida a Drive no funcionará.")
    DRIVE_UTIL_LOADED = False
    # Definir una función dummy para evitar errores si la importación falla, pero la app quedará limitada
    def subir_json_a_drive_especifico(*args, **kwargs):
        st.error("Función de subida a Drive no disponible debido a error de importación.")
        return None
# ------------------------------------------------

def render_chat_libre():
    st.subheader("💬 Chat Libre con GPT")
    st.caption("Conversa libremente, guarda tu historial o súbelo a Google Drive.")

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        logger.error(f"Error al inicializar OpenAI: {e}", exc_info=True)
        st.error(f"Error al inicializar el cliente de OpenAI: {e}.")
        st.error("Asegúrate de haber configurado tu 'openai.api_key' en los secrets de Streamlit.")
        return

    if "chat_libre_history" not in st.session_state:
        st.session_state.chat_libre_history = []
    
    id_proyecto_global_seleccionado = st.session_state.get("id_proyecto_drive_seleccionado", None)
    nombre_proyecto_global_seleccionado = st.session_state.get("nombre_proyecto_seleccionado", None) 
    modelo_gpt_global_preferido = st.session_state.get("modelo_gpt_seleccionado", "gpt-4o")

    with st.sidebar:
        st.markdown("### Opciones del Chat Libre")

        id_proyecto_para_usar_en_drive = None 

        if nombre_proyecto_global_seleccionado and id_proyecto_global_seleccionado:
            st.success(f"Proyecto Activo: **{nombre_proyecto_global_seleccionado}**")
            id_proyecto_para_usar_en_drive = id_proyecto_global_seleccionado
        else:
            st.warning("⚠️ No hay un proyecto global seleccionado. La subida a Drive no estará disponible.")

        modelos_chat_disponibles = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        try:
            default_model_idx = modelos_chat_disponibles.index(modelo_gpt_global_preferido)
        except ValueError:
            default_model_idx = 1 

        modelo_elegido_para_chat = st.selectbox(
            "🤖 Modelo para este Chat:", 
            modelos_chat_disponibles, 
            index=default_model_idx, 
            key="chat_libre_modelo_selector"
        )
        
        st.markdown("---")

        if st.button("💾 Guardar Historial (JSON)", key="chat_libre_guardar_json"):
            if st.session_state.chat_libre_history:
                historial_json_str = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Descargar JSON",
                    data=historial_json_str,
                    file_name=f"historial_chat_libre_{nombre_proyecto_global_seleccionado or 'general'}.json",
                    mime="application/json",
                )
            else:
                st.info("El historial de chat está vacío.")

        subir_drive_deshabilitado = not id_proyecto_para_usar_en_drive or not DRIVE_UTIL_LOADED
        if st.button("☁️ Subir Historial a Drive", disabled=subir_drive_deshabilitado, key="chat_libre_subir_drive"):
            if st.session_state.chat_libre_history:
                nombre_base_archivo = nombre_proyecto_global_seleccionado.replace(" ", "_") if nombre_proyecto_global_seleccionado else "ChatGeneral"
                primer_mensaje_snippet = st.session_state.chat_libre_history[0]['content'][:20].replace(' ','_').replace('/','_').replace('\\','_') if st.session_state.chat_libre_history else "vacio"
                nombre_archivo_drive = f"Historial_{nombre_base_archivo}_{primer_mensaje_snippet}.json"
                
                historial_json_bytes = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2).encode("utf-8")
                
                with st.spinner("Subiendo a Google Drive..."):
                    enlace_drive = subir_json_a_drive_especifico(
                        nombre_archivo=nombre_archivo_drive,
                        contenido_bytes=historial_json_bytes,
                        id_carpeta_proyecto_principal=id_proyecto_para_usar_en_drive,
                        nombre_subcarpeta_destino="chat libre" 
                    )
                if enlace_drive:
                    st.success(f"✅ Historial subido a Drive. [Ver archivo]({enlace_drive})")
                # El error se maneja en la función de Drive si falla
            else:
                st.info("El historial de chat está vacío, nada que subir.")
        
        if subir_drive_deshabilitado:
             st.caption("Para subir a Drive, selecciona un proyecto y asegúrate de que el módulo de Drive esté cargado.")
        
        st.markdown("---") 

        if st.button("🧹 Borrar Historial Actual", type="primary", key="chat_libre_borrar_historial"):
            st.session_state.chat_libre_history = []
            st.success("🧼 Historial de este chat borrado.")
            st.rerun()

    st.markdown("#### Historial de Conversación")
    chat_display_container = st.container(height=400)
    with chat_display_container:
        for mensaje_chat in st.session_state.chat_libre_history:
            with st.chat_message(mensaje_chat["role"]):
                st.markdown(mensaje_chat['content'])

    if user_prompt := st.chat_input("Escribe tu mensaje..."):
        st.session_state.chat_libre_history.append({"role": "user", "content": user_prompt})
        with chat_display_container: 
            with st.chat_message("user"):
                st.markdown(user_prompt)

        with st.spinner("GPT está pensando..."):
            try:
                mensajes_api = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_libre_history]
                
                respuesta_stream = client.chat.completions.create(
                    model=modelo_elegido_para_chat,
                    messages=mensajes_api,
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True
                )
                
                with chat_display_container: 
                    with st.chat_message("assistant"):
                        contenido_completo_respuesta = st.write_stream(respuesta_stream)
                
                st.session_state.chat_libre_history.append({"role": "assistant", "content": contenido_completo_respuesta})
                st.rerun()

            except Exception as e:
                logger.error(f"Error al contactar OpenAI en Chat Libre: {e}", exc_info=True)
                st.error(f"❌ Ha ocurrido un error al contactar con OpenAI: {e}")
                mensaje_error_api = f"Error de API: No se pudo obtener respuesta. ({e})"
                st.session_state.chat_libre_history.append({"role": "assistant", "content": mensaje_error_api})
                with chat_display_container:
                     with st.chat_message("assistant"):
                        st.error(mensaje_error_api)
