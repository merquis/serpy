# modules/gpt/chat_libre_module.py
import streamlit as st
from openai import OpenAI
import json

# Importamos los módulos necesarios.
# Asegúrate de que las rutas y los nombres de las funciones sean correctos.
try:
    from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
    DRIVE_UTILS_LOADED = True
except ImportError:
    # Este st.sidebar.error aparecerá si hay problemas con la importación al inicio.
    st.sidebar.error("Advertencia: Módulo de Drive (drive_utils.py) no encontrado. La subida a Drive estará desactivada.")
    DRIVE_UTILS_LOADED = False
    # Funciones dummy para evitar que la app crashee si la importación falla.
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
    st.sidebar.error("Advertencia: Módulo analizador de archivos no encontrado.")
    ANALIZADOR_LOADED = False
    # Función dummy
    def procesar_archivo_subido():
        st.error("Funcionalidad de análisis de archivos no disponible (error de importación).")
        return None


def render_chat_libre():
    # --- Título y Descripción del Módulo ---
    st.title("💬 Chat Libre Inteligente SERPY") 
    st.markdown("Interactúa con la IA, adjunta archivos para análisis contextual y gestiona tus conversaciones.")

    # --- Inicialización del Cliente OpenAI ---
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except KeyError: # Específicamente si "openai" o "api_key" no están en secrets
        st.error("Error de configuración: Falta la API Key de OpenAI en los secrets de Streamlit.")
        return
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}")
        return

    # --- Inicialización del Estado de Sesión Específico del Módulo ---
    # Usamos prefijos para evitar colisiones con otros módulos si usan claves similares.
    if "chat_libre_historial" not in st.session_state:
        st.session_state.chat_libre_historial = []
    # 'archivo_contexto' es la clave que tu analizador_archivos_module.py actualiza.
    # No necesitamos una copia específica aquí si el analizador siempre usa esa clave.
    if "archivo_contexto" not in st.session_state: 
        st.session_state.archivo_contexto = None
    
    # Para controlar la visibilidad del expander del file uploader
    if "chat_libre_show_uploader" not in st.session_state:
        st.session_state.chat_libre_show_uploader = False
    # Flag para saber si el analizador procesó algo y debemos colapsar el expander
    if "chat_libre_debe_colapsar_uploader" not in st.session_state: # Flag que debe setear tu analizador
        st.session_state.chat_libre_debe_colapsar_uploader = False
    # Buffer para el texto del input personalizado
    if "chat_libre_prompt_buffer_texto" not in st.session_state:
        st.session_state.chat_libre_prompt_buffer_texto = ""


    # --- Configuraciones en la Sidebar ---
    with st.sidebar:
        st.markdown("### ⚙️ Configuración del Chat")
        
        # ID de Proyecto Drive: Se asume que se obtiene de un selector global en streamlit_app.py
        # y se guarda en st.session_state.proyecto_id (o st.session_state.id_proyecto_drive_seleccionado)
        proyecto_id_actual_drive = st.session_state.get("proyecto_id") # Usar la clave que tu app global establece
        nombre_proyecto_actual_drive = st.session_state.get("nombre_proyecto_seleccionado", "Proyecto General") # Nombre para archivos

        if not proyecto_id_actual_drive:
            st.warning("⚠️ No hay proyecto de Drive activo seleccionado globalmente. La subida a Drive no funcionará.")
        # No mostramos el ID aquí, ya que el usuario lo ve en su selector de proyecto principal.

        # Selector de Modelo (usando tu lista de modelos)
        modelos_disponibles = [
            "gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano", 
            "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"
        ]
        # Intentar preseleccionar el modelo global si existe, sino el tuyo por defecto
        modelo_preferido_global = st.session_state.get("modelo_gpt_seleccionado", "gpt-4.1-mini") 
        try:
            indice_default_modelo = modelos_disponibles.index(modelo_preferido_global)
        except ValueError: # Si el modelo global no está en esta lista específica
            indice_default_modelo = modelos_disponibles.index("gpt-4.1-mini") # Tu fallback original

        modelo_seleccionado_chat = st.selectbox(
            "🤖 Modelo IA:",
            modelos_disponibles,
            index=indice_default_modelo,
            key="chat_libre_modelo_selector_sidebar" 
        )
        st.markdown("---") # Separador

    # --- ÁREA PRINCIPAL DEL CHAT ---
    
    # 1. Expander para la Subida y Análisis de Archivos
    # El estado 'expanded' se controla por st.session_state.chat_libre_show_uploader
    with st.expander("📎 Adjuntar archivos para análisis de contexto", expanded=st.session_state.chat_libre_show_uploader):
        if ANALIZADOR_LOADED:
            # La función procesar_archivo_subido() de tu analizador_archivos_module.py
            # renderiza el st.file_uploader y actualiza st.session_state.archivo_contexto.
            # También debe establecer st.session_state.chat_libre_debe_colapsar_uploader = True
            # después de un procesamiento exitoso si queremos que se cierre automáticamente.
            procesar_archivo_subido() 
        else:
            st.error("El módulo para analizar archivos no está disponible.")

        # Verificar si el analizador indicó que se debe colapsar
        if st.session_state.get("chat_libre_debe_colapsar_uploader", False):
            st.session_state.chat_libre_show_uploader = False # Colapsar
            st.session_state.chat_libre_debe_colapsar_uploader = False # Resetear el flag
            st.rerun() # Rerun para que el expander se cierre visualmente

    # 2. Historial de Conversación
    st.markdown("### 📝 Historial de Conversación")
    altura_contenedor_chat = 600 # Altura aumentada para más visibilidad
    contenedor_chat_display = st.container(height=altura_contenedor_chat)

    with contenedor_chat_display:
        if st.session_state.get("archivo_contexto"): # Clave que usa tu analizador
            with st.chat_message("system", avatar="ℹ️"): # Avatar para mensajes del sistema
                st.markdown("*Contexto del archivo adjunto está activo y será considerado por la IA.*")
        
        for mensaje_item in st.session_state.chat_libre_historial: # Usar la clave de historial de este módulo
            with st.chat_message(mensaje_item["role"]):
                st.markdown(mensaje_item["content"])

    # --- BARRA DE INPUT PERSONALIZADA (Estilo Refinado) ---
    st.markdown("---") # Separador visual antes de la barra de input

    contenedor_barra_input = st.container()
    with contenedor_barra_input:
        # Columnas para: [Área de texto] [Botón Clip] [Botón Enviar]
        col_texto_input, col_boton_adjuntar, col_boton_enviar = st.columns([0.75, 0.12, 0.13])

        with col_texto_input:
            # Usar el buffer para el valor del text_area
            prompt_ingresado_usuario = st.text_area(
                "Escribe tu mensaje o pregunta sobre el archivo...", 
                value=st.session_state.chat_libre_prompt_buffer_texto,
                key="chat_libre_input_textarea", 
                height=75, # Altura para aprox. 2-3 líneas de texto
                label_visibility="collapsed" # Ocultar la etiqueta por defecto
            )

        with col_boton_adjuntar:
            # Callback para el botón de adjuntar
            def cambiar_visibilidad_uploader():
                st.session_state.chat_libre_show_uploader = not st.session_state.chat_libre_show_uploader
                # Si se está abriendo, resetear el flag de colapsar
                if st.session_state.chat_libre_show_uploader:
                    st.session_state.chat_libre_debe_colapsar_uploader = False
            
            st.button("📎", key="chat_libre_boton_adjuntar_ui", on_click=cambiar_visibilidad_uploader, help="Adjuntar o ver archivos para contexto", use_container_width=True)

        with col_boton_enviar:
            boton_enviar_presionado = st.button("Enviar ➢", key="chat_libre_boton_enviar_ui", type="primary", use_container_width=True)

    # --- Lógica de Envío y Respuesta del Bot (Funcionalidad sin cambios) ---
    if boton_enviar_presionado and prompt_ingresado_usuario:
        st.session_state.chat_libre_historial.append({"role": "user", "content": prompt_ingresado_usuario})
        st.session_state.chat_libre_prompt_buffer_texto = "" # Limpiar el buffer del input
        # El rerun principal se hará después de la respuesta del bot para mejor fluidez y actualizar el text_area
        # st.rerun() # Quitar este rerun inmediato, confiamos en el de abajo.

    # Procesar respuesta del bot si el último mensaje es del usuario y no se está procesando ya
    if st.session_state.chat_libre_historial and st.session_state.chat_libre_historial[-1]["role"] == "user":
        if not st.session_state.get("chat_libre_procesando_bot", False): # Flag para evitar múltiples llamadas
            st.session_state.chat_libre_procesando_bot = True

            with st.spinner("IA está pensando..."): # Mensaje de spinner más genérico
                try:
                    mensajes_para_api_openai = []
                    if st.session_state.get("archivo_contexto"): # Clave que usa tu analizador
                        mensajes_para_api_openai.append({
                            "role": "system",
                            "content": st.session_state["archivo_contexto"]
                        })
                    
                    for msg_historial_item in st.session_state.chat_libre_historial:
                        mensajes_para_api_openai.append({"role": msg_historial_item["role"], "content": msg_historial_item["content"]})

                    respuesta_openai = client.chat.completions.create(
                        model=modelo_seleccionado_chat, # Usar el modelo seleccionado en la sidebar
                        messages=mensajes_para_api_openai,
                        temperature=0.7,
                        max_tokens=1500, # Ajustar según necesidad
                        stream=True
                    )
                    
                    # Mostrar la respuesta en streaming directamente en el contenedor del chat
                    # Esto requiere que el contenedor ya esté renderizado.
                    # Para asegurar que se añade al final, el rerun es la mejor opción.
                    # La burbuja de chat_message se crea aquí para st.write_stream.
                    with contenedor_chat_display: # Escribir en el contenedor principal
                        with st.chat_message("assistant"): 
                            contenido_completo_respuesta_bot = st.write_stream(respuesta_openai) 
                    
                    st.session_state.chat_libre_historial.append({"role": "assistant", "content": contenido_completo_respuesta_bot})
                
                except Exception as e_openai:
                    mensaje_error_openai = f"❌ Error al contactar con OpenAI: {e_openai}"
                    st.session_state.chat_libre_historial.append({"role": "assistant", "content": mensaje_error_openai})
                finally:
                    st.session_state.chat_libre_procesando_bot = False # Liberar el flag
                    st.rerun() # Rerun final para mostrar todo actualizado y limpiar input buffer

    # --- Botones de Acción Inferiores (Funcionalidad sin cambios, solo asegurar claves únicas) ---
    st.markdown("---") 
    col_descargar, col_subir_drive, col_borrar = st.columns(3)

    with col_descargar:
        contenido_json_para_descarga = json.dumps(st.session_state.chat_libre_historial, ensure_ascii=False, indent=2) if st.session_state.chat_libre_historial else ""
        st.download_button(
            label="⬇️ Descargar Historial", # Más conciso
            file_name=f"historial_chat_{modelo_seleccionado_chat}_{nombre_proyecto_actual_drive}.json",
            mime="application/json",
            data=contenido_json_para_descarga,
            key="chat_libre_boton_descargar_json",
            disabled=not st.session_state.chat_libre_historial,
            use_container_width=True
        )

    with col_subir_drive:
        # Usar el ID del proyecto que ya debería estar en session_state (proyecto_id_actual_drive)
        deshabilitar_boton_drive = not proyecto_id_actual_drive or not st.session_state.chat_libre_historial or not DRIVE_UTILS_LOADED
        
        if st.button("☁️ Subir a Drive", disabled=deshabilitar_boton_drive, key="chat_libre_boton_subir_drive", use_container_width=True):
            contenido_json_para_subir = json.dumps(st.session_state.chat_libre_historial, ensure_ascii=False, indent=2).encode("utf-8")
            nombre_archivo_para_subir = f"Historial_Chat_{modelo_seleccionado_chat}_{nombre_proyecto_actual_drive}.json"
            
            id_subcarpeta = obtener_o_crear_subcarpeta("chat libre", proyecto_id_actual_drive) # Usar la función de drive_utils
            if not id_subcarpeta:
                st.error("❌ No se pudo acceder o crear la subcarpeta 'chat libre' en Drive.")
            else:
                with st.spinner("Subiendo a Google Drive..."):
                    enlace_archivo_drive = subir_json_a_drive(nombre_archivo_para_subir, contenido_json_para_subir, carpeta_id=id_subcarpeta) # Usar la función de drive_utils
                if enlace_archivo_drive:
                    st.success(f"✅ Subido a Drive: [Ver archivo]({enlace_archivo_drive})")
                else:
                    st.error("❌ Error al subir el historial a Drive.")
        elif deshabilitar_boton_drive and st.session_state.chat_libre_historial: # Solo mostrar si hay historial pero falta el ID
            st.caption("ID de Proyecto Drive no configurado o módulo de Drive no disponible.")


    with col_borrar:
        def limpiar_chat_y_contexto():
            st.session_state.chat_libre_historial = []
            st.session_state.archivo_contexto = None # Limpiar contexto del analizador
            st.session_state.chat_libre_show_uploader = False # Ocultar uploader
            st.session_state.chat_libre_prompt_buffer_texto = "" # Limpiar buffer del input
            st.success("Historial y contexto de archivo borrados.")
            # st.rerun() # on_click usualmente maneja el rerun

        st.button(
            "🧹 Borrar Todo", # Más descriptivo
            type="primary",
            key="chat_libre_boton_borrar_todo",
            on_click=limpiar_chat_y_contexto,
            disabled=not st.session_state.chat_libre_historial and not st.session_state.get("archivo_contexto"),
            use_container_width=True
        )

