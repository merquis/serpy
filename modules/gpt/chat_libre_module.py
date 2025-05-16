import streamlit as st
from openai import OpenAI
import json
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
from modules.gpt.analizador_archivos_module import procesar_archivo_subido # Tu módulo de análisis

def render_chat_libre():
    # --- Título y Configuración Inicial (Funcionalidad sin cambios) ---
    st.title("💬 Chat libre con GPT") # Mantener tu título
    st.markdown("Conversación sin restricciones, con historial, carga de archivos y subida a Drive.")

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}")
        return

    # --- Estado Inicial (Funcionalidad sin cambios) ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "archivo_contexto" not in st.session_state:
        st.session_state.archivo_contexto = None
    if "show_file_uploader_chat_libre" not in st.session_state: # Para controlar visibilidad del uploader
        st.session_state.show_file_uploader_chat_libre = False
    
    # --- ID de Proyecto Drive y Modelo desde la Sidebar ---
    # Asumimos que st.session_state.proyecto_id YA ESTÁ SIENDO ESTABLECIDO
    # por tu selector de proyecto global (como "TripToIslands") antes de llamar a esta función.
    # Por lo tanto, NO mostraremos un input manual aquí. Solo la advertencia si no hay proyecto.
    if not st.session_state.get("proyecto_id"): # Usar .get para evitar KeyError si no se inicializó globalmente
        st.sidebar.warning("⚠️ No hay proyecto activo para Drive seleccionado globalmente. La subida a Drive no funcionará.")
    # No mostramos el ID aquí en la sidebar, ya que el usuario lo ve en su selector de proyecto principal.

    # Modelos personalizados (Funcionalidad sin cambios)
    modelos = [
        "gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano", 
        "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"
    ]
    # Intentar preseleccionar el modelo global si existe, sino el tuyo por defecto
    default_model_chat_libre = st.session_state.get("modelo_gpt_seleccionado", "gpt-4.1-mini") # Asume una clave global
    try:
        default_index = modelos.index(default_model_chat_libre)
    except ValueError:
        default_index = modelos.index("gpt-4.1-mini") 

    modelo_seleccionado = st.sidebar.selectbox(
        "🤖 Elige el modelo (Chat Libre)",
        modelos,
        index=default_index,
        key="chat_libre_model_select_sidebar_v3" # Nueva key para evitar conflictos
    )
    # No es necesario llamar a procesar_archivo_subido() aquí arriba. Se integrará en la barra de input.

    # --- ÁREA PRINCIPAL DEL CHAT ---
    
    # 1. Historial de conversación (Funcionalidad sin cambios, altura aumentada)
    st.markdown("### 📝 Historial de conversación")
    chat_container_height = 600 # Altura aumentada
    chat_container = st.container(height=chat_container_height)

    with chat_container:
        if st.session_state.get("archivo_contexto"): # Usar la clave que tu analizador_archivos_module usa
            with st.chat_message("system", avatar="ℹ️"):
                st.markdown("Contexto del archivo adjunto activo.")
        
        for mensaje in st.session_state.chat_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    # --- BARRA DE INPUT PERSONALIZADA (REFINADA) ---
    st.markdown("---") # Separador visual

    input_bar_container = st.container()
    with input_bar_container:
        # Sección para el File Uploader (se muestra/oculta con el botón de clip)
        if st.session_state.show_file_uploader_chat_libre:
            with st.expander("📎 Adjuntar archivos para análisis de contexto", expanded=True):
                # procesar_archivo_subido() de tu analizador_archivos_module.py
                # renderiza el st.file_uploader y actualiza st.session_state.archivo_contexto
                procesar_archivo_subido() 
                if st.session_state.get("archivo_contexto_actualizado_flag", False): # Flag para saber si se procesó algo
                    st.success("Archivo(s) procesados y listos para usarse en el chat.")
                    st.session_state.show_file_uploader_chat_libre = False # Ocultar después de procesar
                    st.session_state.archivo_contexto_actualizado_flag = False # Resetear flag
                    st.rerun() # Para refrescar y ocultar el expander

        # Columnas para la barra de entrada: [Área de texto] [Botón Clip] [Botón Enviar]
        col_input_text, col_attach_button, col_send_button = st.columns([0.75, 0.12, 0.13])

        with col_input_text:
            # Usar una clave única para el text_area para poder limpiarlo si es necesario
            prompt_value = st.session_state.get("chat_libre_prompt_buffer", "")
            prompt = st.text_area(
                "Escribe tu mensaje...", 
                value=prompt_value,
                key="chat_libre_text_area", 
                height=70, # Altura moderada para el área de texto
                label_visibility="collapsed" # Ocultar la etiqueta "Escribe tu mensaje..."
            )

        with col_attach_button:
            def toggle_uploader_visibility():
                st.session_state.show_file_uploader_chat_libre = not st.session_state.show_file_uploader_chat_libre
            
            st.button("📎", key="chat_libre_attach_btn", on_click=toggle_uploader_visibility, help="Adjuntar/Quitar archivos para contexto")

        with col_send_button:
            send_pressed = st.button("Enviar ➢", key="chat_libre_send_btn", type="primary", use_container_width=True)

    # Lógica de envío (Funcionalidad sin cambios, adaptada al nuevo input)
    if send_pressed and prompt: # 'prompt' es el contenido del st.text_area
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.session_state.chat_libre_prompt_buffer = "" # Limpiar el buffer del input
        # st.rerun() # Rerun para mostrar el mensaje del usuario y limpiar el input
        # El rerun principal se hará después de la respuesta del bot para mejor fluidez

    # Procesar respuesta del bot si el último mensaje es del usuario
    # Esta lógica se activa después del rerun si se envió un prompt
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        # Esta condición asegura que solo se llama a la API si hay un nuevo mensaje de usuario
        # y evita llamadas múltiples si otros elementos de la UI causan reruns.
        # Podríamos añadir un flag para asegurar que solo se procesa una vez por mensaje de usuario.
        if not st.session_state.get("processing_bot_response", False):
            st.session_state.processing_bot_response = True # Marcar que estamos procesando

            with st.spinner("GPT está escribiendo..."):
                try:
                    mensajes_chat_api = []
                    if st.session_state.get("archivo_contexto"):
                        mensajes_chat_api.append({
                            "role": "system",
                            "content": st.session_state["archivo_contexto"]
                        })
                    
                    # Enviar todo el historial actual
                    for msg_h in st.session_state.chat_history:
                        mensajes_chat_api.append({"role": msg_h["role"], "content": msg_h["content"]})

                    response = client.chat.completions.create(
                        model=modelo_seleccionado,
                        messages=mensajes_chat_api,
                        temperature=0.7,
                        max_tokens=1500,
                        stream=True
                    )
                    
                    # Para mostrar la respuesta en el lugar correcto (dentro del chat_container)
                    # es mejor que el st.rerun() se encargue de redibujar todo el historial.
                    # st.write_stream necesita un "lugar" donde escribir temporalmente.
                    # Esta burbuja se reemplazará en el siguiente rerun.
                    with st.chat_message("assistant"): 
                        full_response_content = st.write_stream(response) 
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": full_response_content})
                
                except Exception as e:
                    error_msg = f"❌ Error al contactar con OpenAI: {e}"
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                finally:
                    st.session_state.processing_bot_response = False # Desmarcar
                    st.rerun() # Rerun final para mostrar todo actualizado

    # --- Botones inferiores (Funcionalidad sin cambios, solo asegurar claves únicas) ---
    st.markdown("---") 
    col_dl, col_drive, col_clear = st.columns(3)

    with col_dl:
        # ... (código del botón Descargar JSON sin cambios funcionales) ...
        contenido_json_dl_v3 = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2) if st.session_state.chat_history else ""
        st.download_button(
            label="⬇️ Descargar JSON",
            file_name=f"historial_chat_{modelo_seleccionado}_{st.session_state.get('nombre_proyecto_seleccionado', 'General')}.json", # Usa nombre_proyecto_seleccionado
            mime="application/json",
            data=contenido_json_dl_v3,
            key="descargar_json_directo_v3",
            disabled=not st.session_state.chat_history
        )

    with col_drive:
        # ... (código del botón Subir a Drive sin cambios funcionales) ...
        id_proyecto_drive_valido = st.session_state.get("proyecto_id") # El ID que ya tenías
        disabled_drive_button_v3 = not id_proyecto_drive_valido or not st.session_state.chat_history
        
        if st.button("☁️ Subir a Drive", disabled=disabled_drive_button_v3, key="chat_libre_upload_drive_v3"):
            contenido_json_up_v3 = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2).encode("utf-8")
            nombre_archivo_up_v3 = f"Historial_ChatGPT_{modelo_seleccionado}_{st.session_state.get('nombre_proyecto_seleccionado', 'General')}.json" # Usa nombre_proyecto_seleccionado
            
            subcarpeta_id = obtener_o_crear_subcarpeta("chat libre", id_proyecto_drive_valido)
            if not subcarpeta_id:
                st.error("❌ No se pudo acceder o crear la subcarpeta 'chat libre'.")
            else:
                enlace = subir_json_a_drive(nombre_archivo_up_v3, contenido_json_up_v3, carpeta_id=subcarpeta_id)
                if enlace:
                    st.success(f"✅ Subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir a Drive.")
        elif disabled_drive_button_v3 and st.session_state.chat_history:
            st.caption("ID de Proyecto Drive no configurado.")


    with col_clear:
        # ... (código del botón Borrar Historial sin cambios funcionales) ...
        def accion_borrar_chat_v3():
            st.session_state.chat_history = []
            st.session_state.archivo_contexto = None
            st.session_state.show_file_uploader_chat_libre = False 
            st.session_state.chat_libre_prompt_buffer = "" # Limpiar buffer del input
            st.success("Historial y contexto borrados.")

        st.button(
            "🧹 Borrar Historial",
            type="primary",
            key="chat_libre_clear_history_v3",
            on_click=accion_borrar_chat_v3,
            disabled=not st.session_state.chat_history and not st.session_state.get("archivo_contexto")
        )
