# modules/gpt/chat_libre_module.py
import streamlit as st
from openai import OpenAI
import json

# Importamos los módulos necesarios.
# Asegúrate de que las rutas y los nombres de las funciones sean correctos.
try:
    # Asumimos que estas funciones vienen de tu drive_utils.py que usa Cuentas de Servicio
    from modules.utils.drive_utils import subir_json_a_drive_especifico, obtener_o_crear_subcarpeta 
    # Si tu función de subida principal se llama diferente (ej. subir_json_a_drive), ajústalo.
    # Para este ejemplo, usaré subir_json_a_drive_especifico como la que creamos para más claridad.
    # Y obtener_o_crear_subcarpeta para manejar la estructura de carpetas.
    DRIVE_UTILS_LOADED = True
except ImportError:
    st.sidebar.error("Advertencia: Módulo de Drive (drive_utils.py) no encontrado. La subida a Drive estará desactivada.")
    DRIVE_UTILS_LOADED = False
    # Funciones dummy para evitar que la app crashee si la importación falla.
    def subir_json_a_drive_especifico(*args, **kwargs):
        st.error("Funcionalidad de subida a Drive no disponible (error de importación del módulo de Drive).")
        return None
    def obtener_o_crear_subcarpeta(service, nombre_subcarpeta, parent_id): # Ajustar parámetros si es necesario
        st.error("Funcionalidad de creación de carpetas en Drive no disponible (error de importación del módulo de Drive).")
        return None

try:
    # Esta es la función de tu analizador_archivos_v2
    from modules.gpt.analizador_archivos_module import procesar_archivo_subido
    ANALIZADOR_LOADED = True
except ImportError:
    st.sidebar.error("Advertencia: Módulo analizador de archivos no encontrado.")
    ANALIZADOR_LOADED = False
    # Función dummy
    def procesar_archivo_subido():
        st.error("Funcionalidad de análisis de archivos no disponible (error de importación del módulo analizador).")
        return None


def render_chat_libre():
    # --- Título y Descripción del Módulo ---
    st.title("💬 Chat Libre Inteligente SERPY") 
    st.markdown("Interactúa con la IA, adjunta archivos para análisis contextual y gestiona tus conversaciones.")

    # --- Inicialización del Cliente OpenAI ---
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except KeyError: 
        st.error("Error de configuración: Falta la API Key de OpenAI en los secrets de Streamlit.")
        return
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}")
        return

    # --- Inicialización del Estado de Sesión Específico del Módulo ---
    if "chat_libre_historial_vfinal" not in st.session_state: # Clave única para este historial
        st.session_state.chat_libre_historial_vfinal = []
    # 'archivo_contexto' es la clave que tu analizador_archivos_module.py (analizador_archivos_v2) actualiza.
    if "archivo_contexto" not in st.session_state: 
        st.session_state.archivo_contexto = None
    
    if "chat_libre_show_uploader_vfinal" not in st.session_state:
        st.session_state.chat_libre_show_uploader_vfinal = False
    # Flag que debe ser establecido por analizador_archivos_module.py
    if "chat_libre_debe_colapsar_uploader" not in st.session_state: 
        st.session_state.chat_libre_debe_colapsar_uploader = False
    if "chat_libre_prompt_buffer_vfinal" not in st.session_state:
        st.session_state.chat_libre_prompt_buffer_vfinal = ""


    # --- Configuraciones en la Sidebar ---
    with st.sidebar:
        st.markdown("### ⚙️ Configuración del Chat Libre")
        
        # ID de Proyecto Drive: Se asume que se obtiene de un selector global en streamlit_app.py
        # y se guarda en st.session_state.id_proyecto_drive_seleccionado
        proyecto_id_drive_global = st.session_state.get("id_proyecto_drive_seleccionado") 
        nombre_proyecto_drive_global = st.session_state.get("nombre_proyecto_seleccionado", "Proyecto General")

        if not proyecto_id_drive_global:
            st.warning("⚠️ No hay proyecto de Drive activo seleccionado globalmente. La subida a Drive no funcionará.")
        # No mostramos el ID aquí en la sidebar, ya que el usuario lo ve en su selector de proyecto principal.

        modelos_disponibles_chat = [
            "gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano", 
            "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"
        ]
        modelo_preferido_global_chat = st.session_state.get("modelo_gpt_seleccionado", "gpt-4.1-mini") 
        try:
            indice_default_modelo_chat = modelos_disponibles_chat.index(modelo_preferido_global_chat)
        except ValueError: 
            indice_default_modelo_chat = modelos_disponibles_chat.index("gpt-4.1-mini")

        modelo_seleccionado_actual = st.selectbox(
            "🤖 Modelo IA:",
            modelos_disponibles_chat,
            index=indice_default_modelo_chat,
            key="chat_libre_modelo_selector_final" 
        )
        st.markdown("---")

    # --- ÁREA PRINCIPAL DEL CHAT ---
    
    # 1. Expander para la Subida y Análisis de Archivos
    with st.expander("📎 Adjuntar archivos para análisis de contexto", expanded=st.session_state.chat_libre_show_uploader_vfinal):
        if ANALIZADOR_LOADED:
            # Esta función (de analizador_archivos_v2) debe establecer
            # st.session_state.chat_libre_debe_colapsar_uploader = True al finalizar con éxito.
            procesar_archivo_subido() 
        else:
            st.error("El módulo para analizar archivos no está disponible.")

        if st.session_state.get("chat_libre_debe_colapsar_uploader", False):
            st.session_state.chat_libre_show_uploader_vfinal = False 
            st.session_state.chat_libre_debe_colapsar_uploader = False 
            st.rerun() 

    # 2. Historial de Conversación
    st.markdown("### 📝 Historial de Conversación")
    altura_contenedor_chat_actual = 600 
    contenedor_chat_principal = st.container(height=altura_contenedor_chat_actual)

    with contenedor_chat_principal:
        if st.session_state.get("archivo_contexto"): 
            with st.chat_message("system", avatar="ℹ️"): 
                st.markdown("*Contexto del archivo adjunto está activo y será considerado por la IA.*")
        
        for mensaje_item_historial in st.session_state.chat_libre_historial_vfinal:
            with st.chat_message(mensaje_item_historial["role"]):
                st.markdown(mensaje_item_historial["content"])

    # --- BARRA DE INPUT PERSONALIZADA ---
    st.markdown("---") 
    contenedor_barra_input_chat = st.container()
    with contenedor_barra_input_chat:
        col_texto_input_chat, col_boton_adjuntar_chat, col_boton_enviar_chat = st.columns([0.75, 0.12, 0.13])

        with col_texto_input_chat:
            prompt_ingresado_por_usuario = st.text_area(
                "Escribe tu mensaje o pregunta sobre el archivo...", 
                value=st.session_state.chat_libre_prompt_buffer_vfinal,
                key="chat_libre_input_textarea_final", 
                height=75, 
                label_visibility="collapsed"
            )

        with col_boton_adjuntar_chat:
            def cambiar_visibilidad_uploader_chat():
                st.session_state.chat_libre_show_uploader_vfinal = not st.session_state.chat_libre_show_uploader_vfinal
                if st.session_state.chat_libre_show_uploader_vfinal:
                    st.session_state.chat_libre_debe_colapsar_uploader = False
            
            st.button("📎", key="chat_libre_boton_adjuntar_final", on_click=cambiar_visibilidad_uploader_chat, help="Adjuntar o ver archivos para contexto", use_container_width=True)

        with col_boton_enviar_chat:
            boton_enviar_chat_presionado = st.button("Enviar ➢", key="chat_libre_boton_enviar_final", type="primary", use_container_width=True)

    # --- Lógica de Envío y Respuesta del Bot ---
    if boton_enviar_chat_presionado and prompt_ingresado_por_usuario:
        st.session_state.chat_libre_historial_vfinal.append({"role": "user", "content": prompt_ingresado_por_usuario})
        st.session_state.chat_libre_prompt_buffer_vfinal = "" 
        # No es necesario un rerun aquí, el rerun después de la respuesta del bot se encargará.

    if st.session_state.chat_libre_historial_vfinal and st.session_state.chat_libre_historial_vfinal[-1]["role"] == "user":
        if not st.session_state.get("chat_libre_procesando_bot_vfinal", False):
            st.session_state.chat_libre_procesando_bot_vfinal = True

            with st.spinner("IA está pensando..."):
                try:
                    mensajes_para_openai_api = []
                    if st.session_state.get("archivo_contexto"): 
                        mensajes_para_openai_api.append({
                            "role": "system",
                            "content": st.session_state["archivo_contexto"]
                        })
                    
                    for msg_hist_item in st.session_state.chat_libre_historial_vfinal:
                        mensajes_para_openai_api.append({"role": msg_hist_item["role"], "content": msg_hist_item["content"]})

                    respuesta_desde_openai = client.chat.completions.create(
                        model=modelo_seleccionado_actual,
                        messages=mensajes_para_openai_api,
                        temperature=0.7,
                        max_tokens=2000, # Ajustado por si el contexto es largo
                        stream=True
                    )
                    
                    # Mostrar en el contenedor principal del chat
                    with contenedor_chat_principal:
                        with st.chat_message("assistant"): 
                            contenido_respuesta_completa_bot = st.write_stream(respuesta_desde_openai) 
                    
                    st.session_state.chat_libre_historial_vfinal.append({"role": "assistant", "content": contenido_respuesta_completa_bot})
                
                except Exception as e_openai_call:
                    mensaje_error_api_openai = f"❌ Error al contactar con OpenAI: {e_openai_call}"
                    st.session_state.chat_libre_historial_vfinal.append({"role": "assistant", "content": mensaje_error_api_openai})
                finally:
                    st.session_state.chat_libre_procesando_bot_vfinal = False
                    st.rerun() 

    # --- Botones de Acción Inferiores ---
    st.markdown("---") 
    col_descargar_hist, col_subir_hist_drive, col_borrar_hist = st.columns(3)

    with col_descargar_hist:
        contenido_json_para_descarga_final = json.dumps(st.session_state.chat_libre_historial_vfinal, ensure_ascii=False, indent=2) if st.session_state.chat_libre_historial_vfinal else ""
        st.download_button(
            label="⬇️ Descargar Historial",
            file_name=f"historial_chat_{modelo_seleccionado_actual}_{nombre_proyecto_drive_global}.json",
            mime="application/json",
            data=contenido_json_para_descarga_final,
            key="chat_libre_boton_descargar_final",
            disabled=not st.session_state.chat_libre_historial_vfinal,
            use_container_width=True
        )

    with col_subir_hist_drive:
        deshabilitar_boton_subir_drive = not proyecto_id_drive_global or not st.session_state.chat_libre_historial_vfinal or not DRIVE_UTILS_LOADED
        
        if st.button("☁️ Subir a Drive", disabled=deshabilitar_boton_subir_drive, key="chat_libre_boton_subir_drive_final", use_container_width=True):
            contenido_json_para_subir_drive = json.dumps(st.session_state.chat_libre_historial_vfinal, ensure_ascii=False, indent=2).encode("utf-8")
            nombre_archivo_para_subir_drive = f"Historial_Chat_{modelo_seleccionado_actual}_{nombre_proyecto_drive_global}.json"
            
            # Usar la función de drive_utils que crea la subcarpeta "chat libre" y luego sube.
            # Asumimos que proyecto_id_drive_global es el ID de la carpeta principal del proyecto.
            with st.spinner("Subiendo a Google Drive..."):
                # Aquí usas la función que adaptamos para tomar el nombre de la subcarpeta
                enlace_archivo_en_drive = subir_json_a_drive_especifico( 
                    nombre_archivo=nombre_archivo_para_subir_drive,
                    contenido_bytes=contenido_json_para_subir_drive,
                    id_carpeta_proyecto_principal=proyecto_id_drive_global,
                    nombre_subcarpeta_destino="chat libre" # Nombre explícito de la subcarpeta
                )
            if enlace_archivo_en_drive:
                st.success(f"✅ Historial subido a Drive: [Ver archivo]({enlace_archivo_en_drive})")
            # La función subir_json_a_drive_especifico debería manejar sus propios st.error
        elif deshabilitar_boton_subir_drive and st.session_state.chat_libre_historial_vfinal :
            st.caption("Proyecto Drive no seleccionado o módulo de Drive no disponible.")


    with col_borrar_hist:
        def limpiar_todo_chat_libre():
            st.session_state.chat_libre_historial_vfinal = []
            st.session_state.archivo_contexto = None # Limpiar contexto del analizador
            st.session_state.chat_libre_show_uploader_vfinal = False 
            st.session_state.chat_libre_prompt_buffer_vfinal = "" 
            st.success("Historial y contexto de archivo borrados.")

        st.button(
            "🧹 Borrar Todo",
            type="primary",
            key="chat_libre_boton_borrar_final",
            on_click=limpiar_todo_chat_libre,
            disabled=not st.session_state.chat_libre_historial_vfinal and not st.session_state.get("archivo_contexto"),
            use_container_width=True
        )
