# modules/gpt/analizador_archivos_module.py
import streamlit as st
import zipfile
import pandas as pd
import pytesseract # Asegúrate de tener Tesseract OCR instalado en tu sistema
import fitz  # PyMuPDF
import docx
import io
import json
from PIL import Image # Para pytesseract
from lingua import Language, LanguageDetectorBuilder # Para la detección de idioma

# === Configuración de Detección de Idioma ===
# Define los idiomas que quieres que tu aplicación pueda detectar y manejar.
IDIOMAS_OBJETIVO_ANALIZADOR = [
    Language.SPANISH,
    Language.ENGLISH,
    Language.FRENCH,
    Language.GERMAN
    # Puedes añadir más idiomas de la librería lingua si es necesario
]

# Construye el detector de idioma una sola vez cuando se carga el módulo.
try:
    detector_analizador = LanguageDetectorBuilder.from_languages(*IDIOMAS_OBJETIVO_ANALIZADOR).build()
except Exception as e:
    st.error(f"Error al inicializar el detector de idioma en analizador_archivos: {e}")
    # Fallback a un detector nulo si falla la inicialización
    class DetectorNulo:
        def detect_language_of(self, text): return None
    detector_analizador = DetectorNulo()


# === Funciones para Leer Cada Tipo de Archivo ===
# Estas funciones toman un objeto archivo (como el de st.file_uploader)
# y devuelven su contenido como texto.

def leer_txt(archivo_subido):
    """Lee un archivo TXT y devuelve su contenido como string."""
    archivo_subido.seek(0) # Asegurar que empezamos desde el inicio del archivo
    return archivo_subido.read().decode("utf-8", errors="replace") # Usar errors='replace' para evitar fallos

def leer_pdf(archivo_subido):
    """Lee un archivo PDF usando PyMuPDF (fitz) y devuelve el texto extraído."""
    archivo_subido.seek(0)
    contenido_bytes = archivo_subido.read()
    texto_pdf = ""
    try:
        with fitz.open(stream=contenido_bytes, filetype="pdf") as doc_pdf:
            for pagina in doc_pdf:
                texto_pdf += pagina.get_text() + "\n"
    except Exception as e:
        st.warning(f"No se pudo procesar '{archivo_subido.name}' como PDF estándar: {e}. Intentando OCR si es imagen...")
        # Podrías intentar OCR aquí si sospechas que es un PDF de solo imágenes.
        # Por ahora, devolvemos lo que se haya podido extraer.
    return texto_pdf

def leer_docx(archivo_subido):
    """Lee un archivo DOCX y devuelve su contenido como string."""
    archivo_subido.seek(0)
    try:
        # python-docx necesita un stream de bytes o una ruta de archivo.
        # Usamos io.BytesIO para tratar el objeto archivo subido como un stream de bytes.
        documento_docx = docx.Document(io.BytesIO(archivo_subido.read()))
        return "\n".join([parrafo.text for parrafo in documento_docx.paragraphs])
    except Exception as e:
        st.error(f"Error al leer DOCX '{archivo_subido.name}': {e}")
        return ""

def leer_excel(archivo_subido):
    """Lee un archivo Excel (XLSX) y devuelve su contenido como string."""
    archivo_subido.seek(0)
    try:
        # pandas puede leer directamente desde el objeto archivo de Streamlit
        dataframe_excel = pd.read_excel(archivo_subido)
        return dataframe_excel.to_string()
    except Exception as e:
        st.error(f"Error al leer Excel '{archivo_subido.name}': {e}")
        return ""

def leer_csv(archivo_subido):
    """Lee un archivo CSV y devuelve su contenido como string."""
    archivo_subido.seek(0)
    try:
        # pandas puede leer directamente desde el objeto archivo de Streamlit
        # Intentar con diferentes codificaciones si falla UTF-8
        try:
            dataframe_csv = pd.read_csv(archivo_subido)
        except UnicodeDecodeError:
            archivo_subido.seek(0) # Rebobinar para reintentar
            dataframe_csv = pd.read_csv(archivo_subido, encoding='latin1')
        return dataframe_csv.to_string()
    except Exception as e:
        st.error(f"Error al leer CSV '{archivo_subido.name}': {e}")
        return ""

def leer_json_archivo(archivo_subido): # Renombrado para evitar conflicto con el módulo json
    """Lee un archivo JSON y devuelve su contenido como string formateado."""
    archivo_subido.seek(0)
    try:
        datos_json = json.load(archivo_subido) # json.load toma un objeto archivo
        return json.dumps(datos_json, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo JSON '{archivo_subido.name}': {e}")
        return f"Error al procesar JSON: {e}"

def leer_imagen_ocr(archivo_subido): # Renombrado para claridad
    """Lee una imagen usando PIL y extrae texto usando Tesseract OCR."""
    archivo_subido.seek(0)
    try:
        imagen_pil = Image.open(archivo_subido)
        # Podrías añadir preprocesamiento de imagen aquí si es necesario
        return pytesseract.image_to_string(imagen_pil)
    except Exception as e:
        # Verificar si Tesseract está instalado si hay un FileNotFoundError o similar
        if isinstance(e, FileNotFoundError) or "Tesseract is not installed" in str(e):
            st.error("Error de OCR: Tesseract no está instalado o no se encuentra en el PATH del sistema.")
            st.error("Por favor, instala Tesseract OCR y asegúrate de que esté accesible.")
        else:
            st.error(f"❌ Error al procesar imagen '{archivo_subido.name}' con OCR: {e}")
        return ""

def leer_zip_recursivo(archivo_zip_subido): # Renombrado para claridad
    """Lee un archivo ZIP y extrae texto de los archivos soportados en su interior."""
    archivo_zip_subido.seek(0)
    texto_agregado_zip = ""
    try:
        with zipfile.ZipFile(archivo_zip_subido, 'r') as archivo_zip_abierto:
            for nombre_interno in archivo_zip_abierto.namelist():
                # Evitar procesar carpetas o archivos ocultos comunes de macOS
                if nombre_interno.endswith('/') or nombre_interno.startswith('__MACOSX/'):
                    continue

                with archivo_zip_abierto.open(nombre_interno) as archivo_actual_en_zip:
                    # Para que las funciones de lectura funcionen, necesitan un objeto
                    # que se comporte como un archivo subido (con .read(), .name, etc.).
                    # Creamos un objeto BytesIO y le asignamos un nombre.
                    bytes_archivo_interno = archivo_actual_en_zip.read()
                    stream_archivo_interno = io.BytesIO(bytes_archivo_interno)
                    # Simular el atributo 'name' que esperan algunas funciones de lectura
                    stream_archivo_interno.name = nombre_interno 
                    
                    nombre_interno_lower = nombre_interno.lower()
                    contenido_extraido_item = ""

                    if nombre_interno_lower.endswith(".txt"):
                        contenido_extraido_item = leer_txt(stream_archivo_interno)
                    elif nombre_interno_lower.endswith(".pdf"):
                        contenido_extraido_item = leer_pdf(stream_archivo_interno)
                    elif nombre_interno_lower.endswith(".docx"):
                        contenido_extraido_item = leer_docx(stream_archivo_interno)
                    elif nombre_interno_lower.endswith(".xlsx"):
                        contenido_extraido_item = leer_excel(stream_archivo_interno)
                    elif nombre_interno_lower.endswith(".csv"):
                        contenido_extraido_item = leer_csv(stream_archivo_interno)
                    elif nombre_interno_lower.endswith(".json"):
                        contenido_extraido_item = leer_json_archivo(stream_archivo_interno)
                    # No se procesan imágenes dentro de ZIP en esta versión para simplificar,
                    # ya que requeriría pasar el stream de bytes a PIL.

                    if contenido_extraido_item:
                        texto_agregado_zip += f"\n\n--- Contenido de: {nombre_interno} (dentro de {archivo_zip_subido.name}) ---\n{contenido_extraido_item}"
        return texto_agregado_zip
    except zipfile.BadZipFile:
        st.error(f"Error: El archivo '{archivo_zip_subido.name}' no es un ZIP válido o está corrupto.")
        return ""
    except Exception as e:
        st.error(f"Error al procesar archivo ZIP '{archivo_zip_subido.name}': {e}")
        return ""


# === Procesamiento de Archivos Subidos por el Usuario ===
def procesar_archivo_subido():
    """
    Muestra un st.file_uploader y procesa los archivos subidos.
    Actualiza st.session_state.archivo_contexto con el texto extraído.
    Establece st.session_state.chat_libre_debe_colapsar_uploader = True si hay éxito.
    """
    # El título "Subir archivo para análisis" se puede poner en el expander del módulo que llama.
    archivos_subidos_usuario = st.file_uploader(
        "Sube uno o más archivos. El contenido se usará como contexto para el chat.",
        type=["txt", "pdf", "docx", "xlsx", "csv", "json", "zip", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="uploader_central_analizador" # Key única para el widget
    )

    if archivos_subidos_usuario:
        textos_extraidos_completos = []
        nombres_archivos_procesados = []

        with st.spinner("🔄 Analizando archivos... Por favor, espera."):
            for archivo_individual in archivos_subidos_usuario:
                try:
                    nombre_archivo_actual = archivo_individual.name.lower()
                    contenido_del_archivo = ""

                    if nombre_archivo_actual.endswith(".txt"):
                        contenido_del_archivo = leer_txt(archivo_individual)
                    elif nombre_archivo_actual.endswith(".pdf"):
                        contenido_del_archivo = leer_pdf(archivo_individual)
                    elif nombre_archivo_actual.endswith(".docx"):
                        contenido_del_archivo = leer_docx(archivo_individual)
                    elif nombre_archivo_actual.endswith(".xlsx"):
                        contenido_del_archivo = leer_excel(archivo_individual)
                    elif nombre_archivo_actual.endswith(".csv"):
                        contenido_del_archivo = leer_csv(archivo_individual)
                    elif nombre_archivo_actual.endswith(".json"):
                        contenido_del_archivo = leer_json_archivo(archivo_individual)
                    elif nombre_archivo_actual.endswith((".jpg", ".jpeg", ".png")):
                        contenido_del_archivo = leer_imagen_ocr(archivo_individual)
                    elif nombre_archivo_actual.endswith(".zip"):
                        contenido_del_archivo = leer_zip_recursivo(archivo_individual)
                    else:
                        st.warning(f"⚠️ Tipo de archivo no compatible: {archivo_individual.name}")
                        continue 
                    
                    if contenido_del_archivo: # Solo añadir si se extrajo algo
                        textos_extraidos_completos.append(f"--- Inicio del contenido del archivo: {archivo_individual.name} ---\n{contenido_del_archivo}\n--- Fin del contenido del archivo: {archivo_individual.name} ---")
                        nombres_archivos_procesados.append(archivo_individual.name)

                except Exception as e_proc:
                    st.error(f"❌ Error crítico al procesar el archivo `{archivo_individual.name}`: {e_proc}")

        if textos_extraidos_completos:
            contexto_final_para_ia = "\n\n".join(textos_extraidos_completos)
            
            # Detección de idioma del contexto combinado
            idioma_detectado_obj = detector_analizador.detect_language_of(contexto_final_para_ia[:1000]) # Analizar primeros 1000 chars
            idioma_nombre_str = idioma_detectado_obj.name.lower() if idioma_detectado_obj else "unknown"

            # Instrucciones para la IA basadas en el idioma detectado
            instrucciones_por_idioma = {
                "spanish": "El usuario ha subido uno o más archivos para que los analices. A continuación, se presenta el contenido extraído de estos archivos. Debes usar este contenido como la fuente principal de verdad y contexto para responder a las preguntas del usuario relacionadas con estos documentos.",
                "english": "The user has uploaded one or more files for analysis. Below is the extracted content from these files. You should use this content as the primary source of truth and context to answer user questions related to these documents.",
                "french": "L'utilisateur a téléchargé un ou plusieurs fichiers pour analyse. Voici le contenu extrait de ces fichiers. Vous devez utiliser ce contenu comme source principale de vérité et de contexte pour répondre aux questions de l'utilisateur relatives à ces documents.",
                "german": "Der Benutzer hat eine oder mehrere Dateien zur Analyse hochgeladen. Nachfolgend der extrahierte Inhalt aus diesen Dateien. Sie sollten diesen Inhalt als primäre Wahrheitsquelle und Kontext verwenden, um Benutzerfragen zu diesen Dokumenten zu beantworten.",
                "unknown": "The user has uploaded files. The following is the extracted text content. Use this as the primary context for answering questions about these files."
            }

            mensaje_sistema_contexto = instrucciones_por_idioma.get(idioma_nombre_str, instrucciones_por_idioma["unknown"])
            
            # Guardar el contexto completo (instrucción + contenido) en st.session_state
            # Esta es la clave que tu chat_libre_module.py espera.
            st.session_state.archivo_contexto = f"{mensaje_sistema_contexto}\n\n--- INICIO DEL CONTENIDO DE ARCHIVOS ---\n{contexto_final_para_ia}\n--- FIN DEL CONTENIDO DE ARCHIVOS ---"
            
            nombres_str_display = ", ".join(nombres_archivos_procesados)
            st.success(f"✅ Archivo(s) analizado(s): **{nombres_str_display}**. Su contenido se ha añadido al contexto del chat.")
            
            # --- ¡CAMBIO IMPORTANTE AQUÍ! ---
            # Indicar al módulo que llama (chat_libre_module) que el uploader debería colapsarse.
            st.session_state.chat_libre_debe_colapsar_uploader = True
            
            # Opcional: Limpiar el file_uploader para la siguiente subida.
            # Esto es complicado en Streamlit sin cambiar la key del widget, lo que causa un rerun.
            # Por ahora, el usuario tendría que quitar los archivos manualmente del uploader.
            # Si se cambia la key del uploader aquí, causaría un rerun inmediato.
            # Ejemplo: st.session_state.uploader_key_analizador = str(random.randint(1,100000))
            # y usar esa key en st.file_uploader.
            
    # No es necesario devolver nada, ya que se actualiza st.session_state.archivo_contexto
    # y se establece el flag st.session_state.chat_libre_debe_colapsar_uploader.
