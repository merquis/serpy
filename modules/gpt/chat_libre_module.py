# modules/gpt/chat_libre_module.py
import streamlit as st
from openai import OpenAI
import json

# Importaciones (como en tu código original)
try:
    from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
    DRIVE_UTILS_LOADED = True
except ImportError:
    # Este error se mostrará en la sidebar si la importación falla
    st.sidebar.error("Drive utils no disponible. Subida a Drive desactivada.")
    DRIVE_UTILS_LOADED = False
    # Funciones dummy para que la app no falle completamente
    def subir_json_a_drive(*args, **kwargs): 
        st.error("Funcionalidad de subida a Drive no disponible (error de importación).")
        return None
    def obtener_o_crear_subcarpeta(*args, **kwargs): 
        st.error("Funcionalidad de creación de carpetas en Drive no disponible (error de importación).")
        return None

try:
    from modules.gpt.analizador_archivos_module import procesar_archivo_subido
    ANALIZADOR_LOADED = True
except ImportError:
    st.sidebar.error("Analizador de archivos no disponible.")
    ANALIZADOR_LOADED = False
    def procesar_archivo_subido(): 
        st.error("Funcionalidad de análisis de archivos no disponible (error de importación).")

def render_chat_libre():
    # --- Título y Descripción (como en tu código original) ---
    st.title("💬 Chat libre con GPT (desde módulo)")
    st.markdown("Conversación sin restricciones, con historial, carga de archivos y subida a Drive.")

    # --- Inicializar cliente OpenAI (como en tu código original) ---
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}")
        return

    # --- Estado inicial (como en tu código original, con adiciones para la UI) ---
    if "chat_history" not in st.session_state: 
        st.session_state.chat_history = []
    if "archivo_contexto" not in st.session_state: 
        st.session_state.archivo_contexto = None
    
    # Para la UI de subida de archivos en este módulo
    if "chat_libre_show_uploader_ui_v4" not in st.session_state: # Nueva key para esta versión
        st.session_state.chat_libre_show_uploader_ui_v4 = False
    # Flag que debe ser establecido por analizador_archivos_module.py
    # Usamos la misma clave que definimos en analizador_archivos_v3/v4
    if "chat_libre_archivo_procesado_y_colapsar" not in st.session_state: 
        st.session_state.chat_libre_archivo_procesado_y_colapsar = False
    # Buffer para el texto del input personalizado
    if "chat_libre_prompt_buffer_v4" not in st.session_state: 
        st.session_state.chat_libre_prompt_buffer_v4 = ""

    # --- Sidebar: ID Proyecto Drive y Modelo (como en tu código original) ---
    # Esta sección se mantiene como la tenías, ya que indicaste que funciona perfectamente.
    # Si 'proyecto_id' se gestiona globalmente, esta lógica se adaptaría.
    if "proyecto_id" not in st.session_state: # Clave original que usas
        st.session_state.proyecto_id = "" # Inicializar para que el input funcione
        
    st.session_state.proyecto_id = st.sidebar.text_input(
        "ID Proyecto Drive (Opcional)", 
        value=st.session_state.get("proyecto_id", ""), # Mantener valor si existe
        key="chat_libre_project_id" # Tu key original
    )
    if not st.session_state.proyecto_id:
        st.sidebar.warning("⚠️ No hay proyecto activo para Drive.")
    # No es necesario el else con st.sidebar.caption si el usuario ya sabe el proyecto activo
    # por el selector global, o si este input es la única forma de definirlo para este módulo.

    modelos = [ # Tu lista de modelos
        "gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano",
        "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"
    ]
    # Usar el modelo global si existe, sino tu default
    modelo_global_preferido_val = st.session_state.get("modelo_gpt_seleccionado", "gpt-4.1-mini")
    try:
        indice_modelo_default_val = modelos.index(modelo_global_preferido_val)
    except ValueError:
        indice_modelo_default_val = modelos.index("gpt-4.1-mini") # Tu fallback original

    modelo_seleccionado = st.sidebar.selectbox(
        "🤖 Elige el modelo (Chat Libre)",
        modelos,
        index=indice_modelo_default_val,
        key="chat_libre_model_select" # Tu key original
    )
    # La llamada a procesar_archivo_subido() se integra con la barra de input.

    # --- ÁREA PRINCIPAL DEL CHAT ---
    
    # 1. Expander para Subida de Archivos
    with st.expander("📎 Adjuntar archivos para análisis de contexto", expanded=st.session_state.chat_libre_show_uploader_ui_v4):
        if ANALIZADOR_LOADED:
            procesar_archivo_subido() # Esta función usa y actualiza st.session_state.archivo_contexto
                                     # y debe setear st.session_state.chat_libre_archivo_procesado_y_colapsar
        else:
            st.error("El módulo analizador de archivos no está disponible.")

        if st.session_state.get("chat_libre_archivo_procesado_y_colapsar", False):
            st.session_state.chat_libre_show_uploader_ui_v4 = False 
            st.session_state.chat_libre_archivo_procesado_y_colapsar = False 
            st.rerun() 

    # 2. Mostrar historial de conversación (Funcionalidad sin cambios, altura aumentada)
    st.markdown("### 📝 Historial de conversación")
    chat_container_v4 = st.container(height=600) # Altura aumentada
    with chat_container_v4:
        if st.session_state.get("archivo_contexto"): # Usar la clave que tu analizador actualiza
            with st.chat_message("system", avatar="ℹ️"):
                st.markdown("Contexto del archivo adjunto activo.")
        
        for mensaje_item_v4 in st.session_state.chat_history: # Usar tu clave original
            with st.chat_message(mensaje_item_v4["role"]):
                st.markdown(mensaje_item_v4["content"])

    # --- BARRA DE INPUT PERSONALIZADA (REFINADA) ---
    st.markdown("---")
    input_bar_container_v4 = st.container()
    with input_bar_container_v4:
        col_text_area_v4, col_attach_v4, col_send_v4 = st.columns([0.75, 0.12, 0.13])

        with col_text_area_v4:
            prompt_ingresado_v4 = st.text_area(
                "Escribe tu mensaje...",
                value=st.session_state.chat_libre_prompt_buffer_v4,
                key="chat_libre_textarea_input_v4",
                height=70,
                label_visibility="collapsed"
            )

        with col_attach_v4:
            def toggle_uploader_visibility_v4():
                st.session_state.chat_libre_show_uploader_ui_v4 = not st.session_state.chat_libre_show_uploader_ui_v4
                if st.session_state.chat_libre_show_uploader_ui_v4:
                    st.session_state.chat_libre_archivo_procesado_y_colapsar = False
            st.button("📎", key="chat_libre_adjuntar_boton_v4", on_click=toggle_uploader_visibility_v4, help="Adjuntar archivos", use_container_width=True)

        with col_send_v4:
            enviar_presionado_v4 = st.button("Enviar ➢", key="chat_libre_enviar_boton_v4", type="primary", use_container_width=True)

    # --- Lógica de Envío y Respuesta del Bot (Funcionalidad sin cambios, adaptada al nuevo input) ---
    if enviar_presionado_v4 and prompt_ingresado_v4:
        st.session_state.chat_history.append({"role": "user", "content": prompt_ingresado_v4})
        st.session_state.chat_libre_prompt_buffer_v4 = "" # Limpiar buffer
        # El rerun principal se hará después de la respuesta del bot

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        if not st.session_state.get("chat_libre_procesando_bot_v4", False): 
            st.session_state.chat_libre_procesando_bot_v4 = True
            with st.spinner("GPT está escribiendo..."):
                try:
                    mensajes_chat_api_v4 = []
                    if st.session_state.get("archivo_contexto"):
                        mensajes_chat_api_v4.append({
                            "role": "system",
                            "content": st.session_state["archivo_contexto"]
                        })
                    mensajes_chat_api_v4.extend(st.session_state.chat_history)

                    response_openai_v4 = client.chat.completions.create(
                        model=modelo_seleccionado,
                        messages=mensajes_chat_api_v4,
                        temperature=0.7,
                        max_tokens=1500,
                        stream=True
                    )
                    with chat_container_v4: # Escribir en el contenedor correcto
                        with st.chat_message("assistant"):
                            contenido_completo_resp_v4 = st.write_stream(response_openai_v4)
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": contenido_completo_resp_v4})
                except Exception as e_api_v4:
                    msg_error_api_v4 = f"❌ Error al contactar con OpenAI: {e_api_v4}"
                    st.session_state.chat_history.append({"role": "assistant", "content": msg_error_api_v4})
                finally:
                    st.session_state.chat_libre_procesando_bot_v4 = False
                    st.rerun() 

    # --- Botones inferiores (Funcionalidad sin cambios, usando tus claves originales donde sea posible) ---
    st.markdown("---")
    col_btn1_v4, col_btn2_v4, col_btn3_v4 = st.columns(3)

    with col_btn1_v4:
        contenido_json_v4 = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2) if st.session_state.chat_history else ""
        st.download_button(
            label="⬇️ Descargar JSON",
            file_name=f"historial_chat_{modelo_seleccionado}.json", # Tu nombre de archivo original
            mime="application/json",
            data=contenido_json_v4,
            key="descargar_json_directo", # Tu key original
            disabled=not st.session_state.chat_history,
            use_container_width=True
        )

    with col_btn2_v4:
        proyecto_id_drive_v4 = st.session_state.get("proyecto_id") # Tu clave original
        disabled_drive_button_v4 = not proyecto_id_drive_v4 or not st.session_state.chat_history or not DRIVE_UTILS_LOADED
        
        if st.button("☁️ Subir a Google Drive", disabled=disabled_drive_button_v4, key="chat_libre_upload_drive", use_container_width=True): # Tu key original
            contenido_json_drive_v4 = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2).encode("utf-8")
            nombre_archivo_drive_v4 = f"Historial_ChatGPT_{modelo_seleccionado}.json" # Tu nombre de archivo original
            
            # Usar el proyecto_id de session_state que definiste en la sidebar
            subcarpeta_id_drive_v4 = obtener_o_crear_subcarpeta("chat libre", proyecto_id_drive_v4)
            if not subcarpeta_id_drive_v4:
                st.error("❌ No se pudo acceder o crear la subcarpeta 'chat libre' en Drive.")
            else:
                with st.spinner("Subiendo a Google Drive..."):
                    enlace_drive_v4 = subir_json_a_drive(nombre_archivo_drive_v4, contenido_json_drive_v4, carpeta_id=subcarpeta_id_drive_v4)
                if enlace_drive_v4:
                    st.success(f"✅ Subido correctamente: [Ver en Drive]({enlace_drive_v4})")
                else:
                    st.error("❌ Error al subir el historial a Drive.")
        elif disabled_drive_button_v4 and st.session_state.chat_history:
            st.caption("ID de Proyecto no configurado o módulo de Drive no disponible.")


    with col_btn3_v4:
        def accion_borrar_historial_v4(): # Nueva función para la nueva key si es necesario
            st.session_state.chat_history = []
            st.session_state.archivo_contexto = None
            st.session_state.chat_libre_show_uploader_ui_v4 = False 
            st.session_state.chat_libre_prompt_buffer_v4 = ""
            st.success("Historial y contexto borrados.")

        st.button(
            "🧹 Borrar Historial",
            type="primary",
            key="chat_libre_clear_history", # Tu key original
            on_click=accion_borrar_historial_v4, # Tu lambda original adaptada
            disabled=not st.session_state.chat_history and not st.session_state.get("archivo_contexto"), # Lógica de disabled adaptada
            use_container_width=True
        )
