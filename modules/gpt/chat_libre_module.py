import streamlit as st
from openai import OpenAI
import json
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
from modules.gpt.analizador_archivos_module import procesar_archivo_subido # Tu módulo de análisis

def render_chat_libre():
    # --- Título y Configuración Inicial (Sin cambios funcionales) ---
    st.title("💬 Chat Avanzado SERPY") # Título más corto y elegante
    # st.markdown("Conversación con historial, carga de archivos para contexto y subida a Drive.") # Esto puede ser obvio

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}")
        return

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "archivo_contexto" not in st.session_state:
        st.session_state.archivo_contexto = None
    if "show_file_uploader" not in st.session_state: # Para controlar visibilidad del uploader
        st.session_state.show_file_uploader = False
    
    # ID de Proyecto Drive y Modelo desde la Sidebar (como en tu código)
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = "" 
    
    st.session_state.proyecto_id = st.sidebar.text_input(
        "ID Proyecto Drive (Opcional)", 
        value=st.session_state.get("proyecto_id", ""),
        key="chat_libre_project_id_sidebar_input_v2" # Nueva key para evitar conflictos
    )
    if not st.session_state.proyecto_id:
        st.sidebar.warning("⚠️ No hay proyecto activo para Drive.")
    else:
        st.sidebar.caption(f"ID de Drive activo: {st.session_state.proyecto_id}")

    modelos = [
        "gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano", 
        "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"
    ]
    default_model_chat_libre = st.session_state.get("modelo_gpt_seleccionado", "gpt-4.1-mini")
    try:
        default_index = modelos.index(default_model_chat_libre)
    except ValueError:
        default_index = modelos.index("gpt-4.1-mini")

    modelo_seleccionado = st.sidebar.selectbox(
        "🤖 Elige el modelo", # Más corto
        modelos,
        index=default_index,
        key="chat_libre_model_select_sidebar_v2" # Nueva key
    )
    st.sidebar.markdown("---")

    # --- ÁREA PRINCIPAL DEL CHAT ---
    # No llamamos a procesar_archivo_subido() directamente aquí, se integrará en la barra de input.

    # 1. Mostrar historial de conversación
    # st.markdown("### 📝 Historial de conversación") # Título opcional, el chat es evidente
    # Aumentamos la altura del contenedor del chat para hacerlo más grande
    chat_container_height = 650 # <--- ALTURA AUMENTADA SIGNIFICATIVAMENTE
    chat_container = st.container(height=chat_container_height)

    with chat_container:
        if st.session_state.get("archivo_contexto"):
            with st.chat_message("system", avatar="ℹ️"):
                st.markdown("Contexto del archivo adjunto activo. Puedes preguntar sobre él o seguir la conversación.")
        
        for mensaje in st.session_state.chat_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    # --- BARRA DE INPUT PERSONALIZADA (REEMPLAZA st.chat_input) ---
    st.markdown("---") # Separador visual antes de la barra de input

    # Contenedor para la barra de input y el file_uploader (si está visible)
    input_area_container = st.container()

    with input_area_container:
        # Si se debe mostrar el file_uploader
        if st.session_state.show_file_uploader:
            with st.expander("📎 Adjuntar y Analizar Archivos (el contexto se añadirá al chat)", expanded=True):
                # La función procesar_archivo_subido() de tu módulo analizador_archivos_module.py
                # renderiza el st.file_uploader y maneja la lógica de actualización de 
                # st.session_state.archivo_contexto
                procesar_archivo_subido() 
                if st.session_state.get("archivo_contexto"):
                    st.success("Archivo(s) procesados. Su contenido se usará como contexto.")
                    # Opcional: botón para cerrar el uploader después de procesar
                    if st.button("Hecho con la subida", key="done_uploading_btn"):
                        st.session_state.show_file_uploader = False
                        st.rerun() # Para ocultar el expander inmediatamente

        # Fila para el input de texto y botones
        col_text, col_attach, col_send = st.columns([0.75, 0.1, 0.15])

        with col_text:
            prompt = st.text_area("Escribe tu mensaje...", key="custom_chat_input_text", height=75, 
                                  placeholder="Pregunta sobre el archivo o inicia una conversación...")
        
        with col_attach:
            # Botón para mostrar/ocultar el file_uploader
            # Usamos un callback para cambiar el estado y forzar un rerun
            def toggle_file_uploader():
                st.session_state.show_file_uploader = not st.session_state.show_file_uploader
            
            st.button("📎", key="attach_file_btn", on_click=toggle_file_uploader, help="Adjuntar archivo para contexto")

        with col_send:
            send_button_pressed = st.button("Enviar ➢", key="send_custom_chat_btn", type="primary")

    # Lógica de envío del mensaje (cuando se presiona el botón "Enviar")
    if send_button_pressed and prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        # Limpiar el text_area después de enviar (esto requiere un truco o rerun)
        # Por ahora, el texto permanecerá, el usuario deberá borrarlo.
        # Para limpiar, se podría hacer st.session_state.custom_chat_input_text = "" y st.rerun()
        # pero eso interrumpe el flujo inmediato de mostrar el mensaje del user.
        # Es más simple que el rerun después de la respuesta del bot limpie el flujo.
        
        # Forzar rerun para mostrar el mensaje del usuario inmediatamente ANTES del spinner
        # y limpiar el prompt si así se desea (aunque esto hace doble rerun)
        # st.session_state.custom_chat_input_text_value = prompt # Guardar para re-mostrar
        # st.text_area("Escribe tu mensaje...", value="", key="custom_chat_input_text_cleared") # No funciona bien para limpiar
        st.rerun() # Esto mostrará el mensaje del usuario en el chat_container

    # Procesar respuesta del bot si el último mensaje es del usuario
    # Esto se ejecutará después del rerun si se envió un prompt
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        with st.spinner("GPT está escribiendo..."):
            try:
                mensajes_chat = []
                if st.session_state.get("archivo_contexto"):
                    mensajes_chat.append({
                        "role": "system",
                        "content": st.session_state["archivo_contexto"]
                    })
                
                for msg_hist in st.session_state.chat_history:
                     mensajes_chat.append({"role": msg_hist["role"], "content": msg_hist["content"]})

                response = client.chat.completions.create(
                    model=modelo_seleccionado,
                    messages=mensajes_chat,
                    temperature=0.7,
                    max_tokens=1500,
                    stream=True
                )
                
                # Para mostrar la respuesta en el lugar correcto (dentro del chat_container)
                # es mejor que el st.rerun() se encargue de redibujar todo el historial.
                # Aquí solo capturamos el contenido.
                with st.chat_message("assistant"): # Esto es temporal para write_stream
                    full_response_content = st.write_stream(response) 
                
                st.session_state.chat_history.append({"role": "assistant", "content": full_response_content})
                st.rerun()

            except Exception as e:
                error_msg = f"❌ Error al contactar con OpenAI: {e}"
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                st.rerun() # Para mostrar el error en el historial

    # --- Botones inferiores (funcionalidad sin cambios) ---
    st.markdown("---") 
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        # ... (código del botón Descargar JSON sin cambios) ...
        contenido_json_dl = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2) if st.session_state.chat_history else ""
        st.download_button(
            label="⬇️ Descargar JSON",
            file_name=f"historial_chat_{modelo_seleccionado}_{st.session_state.get('nombre_proyecto_seleccionado', 'General')}.json",
            mime="application/json",
            data=contenido_json_dl,
            key="chat_libre_descargar_json_btn_v2", # Nueva key
            disabled=not st.session_state.chat_history
        )

    with col_btn2:
        # ... (código del botón Subir a Drive sin cambios funcionales) ...
        id_proyecto_drive_para_subida = st.session_state.get("proyecto_id") 
        disabled_drive_button_ui = not id_proyecto_drive_para_subida or not st.session_state.chat_history
        
        if st.button("☁️ Subir a Drive", disabled=disabled_drive_button_ui, key="chat_libre_upload_drive_btn_v2"): # Nueva key
            contenido_json_up = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2).encode("utf-8")
            nombre_archivo_up = f"Historial_ChatGPT_{modelo_seleccionado}_{st.session_state.get('nombre_proyecto_seleccionado', 'General')}.json"
            
            subcarpeta_id = obtener_o_crear_subcarpeta("chat libre", id_proyecto_drive_para_subida)
            if not subcarpeta_id:
                st.error("❌ No se pudo acceder o crear la subcarpeta 'chat libre' en Drive.")
            else:
                enlace = subir_json_a_drive(nombre_archivo_up, contenido_json_up, carpeta_id=subcarpeta_id)
                if enlace:
                    st.success(f"✅ Subido: [Ver en Drive]({enlace})") # Más corto
                else:
                    st.error("❌ Error al subir a Drive.")
        elif disabled_drive_button_ui and st.session_state.chat_history : 
            st.caption("Ingresa ID de Proyecto en sidebar para subir.")


    with col_btn3:
        # ... (código del botón Borrar Historial sin cambios funcionales) ...
        def accion_borrar_chat_libre_v2(): # Nueva función para nueva key
            st.session_state.chat_history = []
            st.session_state.archivo_contexto = None 
            st.session_state.show_file_uploader = False # Ocultar uploader también
            st.success("Historial y contexto borrados.")

        st.button(
            "🧹 Borrar Historial",
            type="primary",
            key="chat_libre_clear_history_btn_v2", # Nueva key
            on_click=accion_borrar_chat_libre_v2,
            disabled=not st.session_state.chat_history and not st.session_state
