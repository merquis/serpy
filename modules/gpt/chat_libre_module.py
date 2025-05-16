# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI
import json

# Importa tu función específica de Drive desde tu módulo de utilidades de Drive
# Asegúrate de que este módulo y la función existan y funcionen como se espera.
try:
    from modules.utils.drive_utils import subir_json_a_drive_especifico
except ImportError:
    # Fallback a una simulación si el módulo de drive_utils no está o falla la importación
    st.warning("Advertencia: No se pudo importar 'subir_json_a_drive_especifico' desde 'modules.utils.drive_utils'. Se usará una simulación para la subida a Drive.")
    def subir_json_a_drive_especifico(nombre_archivo: str, 
                                     contenido_bytes: bytes, 
                                     id_carpeta_proyecto_principal: str, 
                                     nombre_subcarpeta_destino: str):
        st.info(f"Simulación: Subiendo '{nombre_archivo}' a Drive (Proyecto ID: {id_carpeta_proyecto_principal}, Subcarpeta: {nombre_subcarpeta_destino})...")
        if not id_carpeta_proyecto_principal:
            st.error("Simulación: ID de proyecto principal no proporcionado.")
            return None
        return f"https://drive.google.com/mock_link_for_{nombre_archivo.replace(' ', '_')}"

def render_chat_libre():
    # El título principal del módulo usualmente se pone en streamlit_app.py
    # al seleccionar este módulo. Aquí podemos poner un subtítulo o una descripción.
    st.subheader("💬 Chat Libre con GPT")
    st.caption("Conversa libremente, guarda tu historial o súbelo a Google Drive.")

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar el cliente de OpenAI: {e}.")
        st.error("Asegúrate de haber configurado tu 'openai.api_key' en los secrets de Streamlit.")
        return

    # Inicializar el historial de chat específico para este módulo si no existe
    if "chat_libre_history" not in st.session_state:
        st.session_state.chat_libre_history = []
    
    # Obtener el ID y nombre del proyecto seleccionado globalmente desde st.session_state
    # Estos deben ser establecidos por tu widget de navegación de proyectos en streamlit_app.py
    id_proyecto_global_seleccionado = st.session_state.get("id_proyecto_drive_seleccionado", None)
    nombre_proyecto_global_seleccionado = st.session_state.get("nombre_proyecto_seleccionado", None) 

    # Obtener el modelo GPT seleccionado globalmente (o usar un default)
    modelo_gpt_global_preferido = st.session_state.get("modelo_gpt_seleccionado", "gpt-4o")

    # --- Sección de la Barra Lateral: Opciones del Chat Libre ---
    with st.sidebar:
        st.markdown("### Opciones del Chat Libre")

        id_proyecto_para_usar_en_drive = None # Variable para almacenar el ID de Drive que se usará

        if nombre_proyecto_global_seleccionado and id_proyecto_global_seleccionado:
            st.success(f"Proyecto Activo: **{nombre_proyecto_global_seleccionado}**")
            id_proyecto_para_usar_en_drive = id_proyecto_global_seleccionado
        else:
            # Si no hay proyecto global, la subida a Drive se deshabilitará más adelante.
            # No mostramos el input manual para mantener la lógica de que el ID se coge automáticamente.
            st.warning("⚠️ No hay un proyecto global seleccionado. La subida a Drive no estará disponible.")

        # Selector de modelo para este chat, preseleccionando el global si es posible
        modelos_chat_disponibles = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        try:
            default_model_idx = modelos_chat_disponibles.index(modelo_gpt_global_preferido)
        except ValueError:
            default_model_idx = 1 # Fallback a gpt-4o

        modelo_elegido_para_chat = st.selectbox(
            "🤖 Modelo para este Chat:", 
            modelos_chat_disponibles, 
            index=default_model_idx, 
            key="chat_libre_modelo_selector"
        )
        
        st.markdown("---") # Separador visual

        # Botón para guardar el historial como JSON localmente
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

        # Botón para subir el historial a Google Drive
        # Se deshabilita si no hay un proyecto global (id_proyecto_para_usar_en_drive es None)
        subir_drive_deshabilitado = not id_proyecto_para_usar_en_drive
        if st.button("☁️ Subir Historial a Drive", disabled=subir_drive_deshabilitado, key="chat_libre_subir_drive"):
            if st.session_state.chat_libre_history:
                nombre_base_archivo = nombre_proyecto_global_seleccionado.replace(" ", "_") if nombre_proyecto_global_seleccionado else "ChatGeneral"
                # Crear un nombre de archivo un poco más descriptivo
                primer_mensaje_snippet = st.session_state.chat_libre_history[0]['content'][:20].replace(' ','_').replace('/','_').replace('\\','_') if st.session_state.chat_libre_history else "vacio"
                nombre_archivo_drive = f"Historial_{nombre_base_archivo}_{primer_mensaje_snippet}.json"
                
                historial_json_bytes = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2).encode("utf-8")
                
                with st.spinner("Subiendo a Google Drive..."):
                    enlace_drive = subir_json_a_drive_especifico(
                        nombre_archivo=nombre_archivo_drive,
                        contenido_bytes=historial_json_bytes,
                        id_carpeta_proyecto_principal=id_proyecto_para_usar_en_drive, # ID de la carpeta "TripToIslands"
                        nombre_subcarpeta_destino="chat libre" # Nombre de la subcarpeta deseada
                    )
                if enlace_drive:
                    st.success(f"✅ Historial subido a Drive. [Ver archivo]({enlace_drive})")
                # La función subir_json_a_drive_especifico ya debería mostrar errores si los hay
            else:
                st.info("El historial de chat está vacío, nada que subir.")
        
        if subir_drive_deshabilitado:
             st.caption("Para subir a Drive, primero selecciona un proyecto en la navegación principal.")
        
        st.markdown("---") # Separador visual

        # Botón para borrar el historial del chat actual
        if st.button("🧹 Borrar Historial Actual", type="primary", key="chat_libre_borrar_historial"):
            st.session_state.chat_libre_history = []
            st.success("🧼 Historial de este chat borrado.")
            st.rerun() # Para refrescar la vista del chat

    # --- Cuerpo Principal del Chat ---
    st.markdown("#### Historial de Conversación")
    # Contenedor para el chat con altura fija y scroll
    chat_display_container = st.container(height=400)
    with chat_display_container:
        for mensaje_chat in st.session_state.chat_libre_history:
            with st.chat_message(mensaje_chat["role"]):
                st.markdown(mensaje_chat['content'])

    # Input para el mensaje del usuario
    if user_prompt := st.chat_input("Escribe tu mensaje..."):
        # Añadir mensaje del usuario al historial y mostrarlo
        st.session_state.chat_libre_history.append({"role": "user", "content": user_prompt})
        with chat_display_container: # Actualizar visualización inmediatamente
            with st.chat_message("user"):
                st.markdown(user_prompt)

        # Procesar respuesta del asistente
        with st.spinner("GPT está pensando..."):
            try:
                # Preparar mensajes para la API (solo el historial actual de este chat)
                mensajes_api = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_libre_history]
                
                respuesta_stream = client.chat.completions.create(
                    model=modelo_elegido_para_chat,
                    messages=mensajes_api,
                    temperature=0.7,
                    max_tokens=2000, # Puedes ajustar esto
                    stream=True
                )
                
                # Mostrar la respuesta en streaming
                with chat_display_container: # Mostrar dentro del contenedor
                    with st.chat_message("assistant"):
                        contenido_completo_respuesta = st.write_stream(respuesta_stream)
                
                # Añadir respuesta completa al historial
                st.session_state.chat_libre_history.append({"role": "assistant", "content": contenido_completo_respuesta})
                st.rerun() # Refrescar para asegurar que todo el estado se actualice bien

            except Exception as e:
                st.error(f"❌ Ha ocurrido un error al contactar con OpenAI: {e}")
                mensaje_error_api = f"Error de API: No se pudo obtener respuesta. ({e})"
                st.session_state.chat_libre_history.append({"role": "assistant", "content": mensaje_error_api})
                # Mostrar el error también en el chat
                with chat_display_container:
                     with st.chat_message("assistant"):
                        st.error(mensaje_error_api)
