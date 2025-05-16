import streamlit as st
from openai import OpenAI
# Importa las librerías necesarias para procesar archivos, ej:
# import PyPDF2
# from docx import Document
import io # Para manejar bytes de archivos en memoria

# (Aquí iría tu inicialización de cliente OpenAI, manejo de API key, etc.)
# client = OpenAI(api_key=st.secrets["openai"]["api_key"])

def procesar_archivo_subido(uploaded_file):
    """
    Procesa el archivo subido y extrae su texto.
    Esta es una función simplificada. Necesitarás expandirla.
    """
    contenido = ""
    if uploaded_file is not None:
        st.write(f"Archivo subido: {uploaded_file.name} ({uploaded_file.type})")
        
        # Leer bytes del archivo
        bytes_data = uploaded_file.getvalue()
        
        if uploaded_file.type == "text/plain":
            contenido = bytes_data.decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            # Aquí usarías PyPDF2 o similar
            # Ejemplo muy básico (necesitarías instalar PyPDF2: pip install PyPDF2)
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(bytes_data))
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    contenido += page.extract_text()
            except Exception as e:
                st.error(f"Error al procesar PDF: {e}")
                return None
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Aquí usarías python-docx o similar
            # Ejemplo muy básico (necesitarías instalar python-docx: pip install python-docx)
            try:
                from docx import Document
                doc = Document(io.BytesIO(bytes_data))
                for para in doc.paragraphs:
                    contenido += para.text + "\n"
            except Exception as e:
                st.error(f"Error al procesar DOCX: {e}")
                return None
        # Añadir más tipos de archivo según necesites
        else:
            st.warning(f"Tipo de archivo '{uploaded_file.type}' no soportado para procesamiento directo de texto.")
            return None
            
        # st.text_area("Contenido extraído (primeros 1000 caracteres):", contenido[:1000], height=150)
        return contenido
    return None

def render_chat_con_archivos():
    st.title("💬 Chat con tus Archivos")

    # --- Configuración de OpenAI (debe estar fuera de la función si es global) ---
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Configura 'openai.api_key'.")
        return

    # --- Sección de Subida de Archivo ---
    # Usamos session_state para mantener el contenido del archivo entre reruns
    if "contenido_archivo" not in st.session_state:
        st.session_state.contenido_archivo = None
    if "nombre_archivo" not in st.session_state:
        st.session_state.nombre_archivo = None

    # Coloca el file_uploader en la sidebar o en el cuerpo principal
    with st.sidebar:
        st.header("📂 Sube tu Archivo")
        uploaded_file = st.file_uploader("Elige un archivo (txt, pdf, docx)", type=["txt", "pdf", "docx"])

        if uploaded_file is not None:
            # Si se sube un nuevo archivo, procesarlo
            if st.session_state.nombre_archivo != uploaded_file.name:
                with st.spinner(f"Procesando {uploaded_file.name}..."):
                    st.session_state.contenido_archivo = procesar_archivo_subido(uploaded_file)
                    st.session_state.nombre_archivo = uploaded_file.name
                    if st.session_state.contenido_archivo:
                        st.success(f"'{uploaded_file.name}' procesado y listo para preguntas.")
                        # Limpiar historial de chat si se sube un nuevo archivo
                        st.session_state.chat_history_archivos = [] 
                    else:
                        st.error(f"No se pudo extraer contenido de '{uploaded_file.name}'.")
        
        if st.session_state.nombre_archivo:
            st.write(f"Archivo cargado: **{st.session_state.nombre_archivo}**")
            if st.button("Quitar archivo", key="quitar_archivo"):
                st.session_state.contenido_archivo = None
                st.session_state.nombre_archivo = None
                st.session_state.chat_history_archivos = [] # Limpiar historial también
                st.rerun()


    # --- Historial de Chat ---
    if "chat_history_archivos" not in st.session_state:
        st.session_state.chat_history_archivos = []

    st.markdown("### Conversación")
    chat_container = st.container(height=400)
    with chat_container:
        for mensaje in st.session_state.chat_history_archivos:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje['content'])

    # --- Input del Usuario ---
    if prompt := st.chat_input("Haz una pregunta sobre el archivo..."):
        if st.session_state.contenido_archivo is None:
            st.warning("Por favor, sube y procesa un archivo primero.")
        else:
            st.session_state.chat_history_archivos.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

            with st.spinner("Pensando..."):
                try:
                    # Construir el prompt para el modelo
                    # Es importante ser explícito con el modelo sobre el contexto
                    mensajes_para_api = [
                        {"role": "system", "content": f"Eres un asistente útil. El usuario ha subido un archivo llamado '{st.session_state.nombre_archivo}'. Usa el siguiente contenido del archivo para responder a sus preguntas: \n\n---INICIO DEL CONTENIDO DEL ARCHIVO---\n{st.session_state.contenido_archivo}\n---FIN DEL CONTENIDO DEL ARCHIVO---"},
                        # Podrías añadir el historial de chat aquí si quieres que sea conversacional
                        # sobre el mismo archivo, o solo la última pregunta.
                        # Ejemplo con solo la última pregunta (más simple para empezar):
                        {"role": "user", "content": prompt}
                    ]
                    
                    # Si quieres mantener la conversación sobre el archivo:
                    # mensajes_para_api = [
                    #    {"role": "system", "content": f"Eres un asistente útil. ... (contexto del archivo) ..."},
                    # ]
                    # mensajes_para_api.extend(st.session_state.chat_history_archivos) # Añade el historial

                    response_stream = client.chat.completions.create(
                        model="gpt-4o", # o el modelo que prefieras
                        messages=mensajes_para_api,
                        stream=True
                    )
                    
                    with chat_container:
                        with st.chat_message("assistant"):
                            full_response_content = st.write_stream(response_stream)
                    
                    st.session_state.chat_history_archivos.append({"role": "assistant", "content": full_response_content})
                    # st.rerun() # Opcional, write_stream ya actualiza

                except Exception as e:
                    st.error(f"❌ Error al contactar con OpenAI: {e}")
                    st.session_state.chat_history_archivos.append({"role": "assistant", "content": f"Error: {e}"})

# Para probar este módulo directamente:
# if __name__ == "__main__":
#     # Necesitarás configurar tus secrets de OpenAI aquí o globalmente
#     # Ejemplo: st.secrets["openai"] = {"api_key": "sk-..."}
#     render_chat_con_archivos()
