# modules/gpt/chat_con_archivos_module.py

import streamlit as st
from openai import OpenAI
import io # Para manejar bytes de archivos en memoria

# Importa las librerías necesarias para procesar archivos
try:
    import PyPDF2 # pip install PyPDF2
except ImportError:
    st.error("Librería PyPDF2 no encontrada. Por favor, instálala: pip install PyPDF2")
    PyPDF2 = None # Para evitar más errores si no está

try:
    from docx import Document # pip install python-docx
except ImportError:
    st.error("Librería python-docx no encontrada. Por favor, instálala: pip install python-docx")
    Document = None # Para evitar más errores


def procesar_archivo_subido(uploaded_file):
    contenido = ""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        
        if uploaded_file.type == "text/plain":
            try:
                contenido = bytes_data.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    contenido = bytes_data.decode("latin-1") # Intenta con otra codificación común
                except Exception as e:
                    st.error(f"Error al decodificar archivo de texto: {e}")
                    return None
        elif uploaded_file.type == "application/pdf":
            if PyPDF2 is None: return None # Si la librería no se importó
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(bytes_data))
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    contenido += page.extract_text() or "" # Añadir 'or ""' por si extract_text devuelve None
            except Exception as e:
                st.error(f"Error al procesar PDF: {e}")
                return None
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            if Document is None: return None # Si la librería no se importó
            try:
                doc = Document(io.BytesIO(bytes_data))
                for para in doc.paragraphs:
                    contenido += para.text + "\n"
            except Exception as e:
                st.error(f"Error al procesar DOCX: {e}")
                return None
        else:
            st.warning(f"Tipo de archivo '{uploaded_file.type}' no soportado para extracción de texto directa.")
            return None
        
        if not contenido.strip():
            st.warning("No se pudo extraer texto del archivo o el archivo está vacío.")
            return None
            
        return contenido
    return None

def render_chat_con_archivos():
    st.header("💬 Chat con tus Archivos")
    st.markdown("Sube un archivo (TXT, PDF, DOCX) y haz preguntas sobre su contenido.")

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Configura 'openai.api_key'.")
        return

    if "chat_archivos_history" not in st.session_state:
        st.session_state.chat_archivos_history = []
    if "chat_archivos_contenido" not in st.session_state:
        st.session_state.chat_archivos_contenido = None
    if "chat_archivos_nombre" not in st.session_state:
        st.session_state.chat_archivos_nombre = None

    with st.sidebar:
        st.subheader("Archivo para Chat")
        uploaded_file = st.file_uploader(
            "Sube un archivo", 
            type=["txt", "pdf", "docx"], 
            key="uploader_chat_archivos"
        )

        if uploaded_file is not None:
            if st.session_state.chat_archivos_nombre != uploaded_file.name: # Nuevo archivo o cambio de archivo
                with st.spinner(f"Procesando '{uploaded_file.name}'..."):
                    contenido = procesar_archivo_subido(uploaded_file)
                    if contenido:
                        st.session_state.chat_archivos_contenido = contenido
                        st.session_state.chat_archivos_nombre = uploaded_file.name
                        st.session_state.chat_archivos_history = [] # Resetear historial para nuevo archivo
                        st.success(f"'{uploaded_file.name}' procesado. ¡Listo para tus preguntas!")
                    else:
                        st.session_state.chat_archivos_contenido = None # Asegurar que esté limpio si falla
                        st.session_state.chat_archivos_nombre = None
                        st.error(f"No se pudo extraer contenido de '{uploaded_file.name}'.")
        
        if st.session_state.chat_archivos_nombre:
            st.info(f"Archivo cargado: **{st.session_state.chat_archivos_nombre}**")
            if st.button("Quitar archivo cargado", key="sidebar_chat_archivos_quitar"):
                st.session_state.chat_archivos_contenido = None
                st.session_state.chat_archivos_nombre = None
                st.session_state.chat_archivos_history = []
                st.rerun()
        
        st.markdown("---")
        modelos_archivos = ["gpt-4o", "gpt-3.5-turbo-16k", "gpt-4-turbo"] # Modelos con contexto más largo son mejores
        modelo_seleccionado_archivos = st.selectbox(
            "🤖 Elige el modelo (Chat con Archivos)", 
            modelos_archivos, 
            index=0, 
            key="sidebar_chat_archivos_model_select",
            help="Modelos con mayor ventana de contexto como gpt-4o o gpt-4-turbo son recomendados."
        )


    chat_container_archivos = st.container(height=450)
    with chat_container_archivos:
        for mensaje in st.session_state.chat_archivos_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje['content'])

    if prompt := st.chat_input("Haz una pregunta sobre el archivo..."):
        if st.session_state.chat_archivos_contenido is None:
            st.warning("Por favor, sube y procesa un archivo primero.")
        else:
            st.session_state.chat_archivos_history.append({"role": "user", "content": prompt})
            with chat_container_archivos:
                with st.chat_message("user"):
                    st.markdown(prompt)

            with st.spinner("GPT (Chat con Archivos) está pensando..."):
                try:
                    # Preparamos el historial para la API, incluyendo el system prompt con el contexto del archivo
                    mensajes_para_api = [
                        {"role": "system", 
                         "content": f"Eres un asistente experto en responder preguntas basándote en el contenido de un documento proporcionado. El documento se llama '{st.session_state.chat_archivos_nombre}'. A continuación, se presenta el contenido del documento:\n\n---INICIO DEL CONTENIDO DEL ARCHIVO---\n{st.session_state.chat_archivos_contenido}\n---FIN DEL CONTENIDO DEL ARCHIVO---\n\nResponde las preguntas del usuario basándote ÚNICAMENTE en este contenido. Si la respuesta no se encuentra en el texto, indícalo claramente."}
                    ]
                    # Añadir historial de la conversación actual sobre el archivo
                    for msg in st.session_state.chat_archivos_history:
                        if msg["role"] != "system": # Evitar duplicar system prompts si se guardaran
                             mensajes_para_api.append({"role": msg["role"], "content": msg["content"]})
                    
                    # Asegurarse de que el último mensaje sea el prompt del usuario si no se incluyó arriba
                    if mensajes_para_api[-1]["role"] == "assistant":
                         mensajes_para_api.append({"role": "user", "content": prompt})


                    response = client.chat.completions.create(
                        model=modelo_seleccionado_archivos,
                        messages=mensajes_para_api,
                        stream=True
                    )
                    
                    with chat_container_archivos:
                        with st.chat_message("assistant"):
                            full_response_content = st.write_stream(response)
                    
                    st.session_state.chat_archivos_history.append({"role": "assistant", "content": full_response_content})

                except Exception as e:
                    st.error(f"❌ Error con OpenAI (Chat con Archivos): {e}")
                    error_msg = f"Error de API: {e}"
                    st.session_state.chat_archivos_history.append({"role": "assistant", "content": error_msg})
                    with chat_container_archivos:
                        with st.chat_message("assistant"):
                            st.error(error_msg)
