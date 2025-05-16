# modules/gpt/analizador_archivos_module.py
import streamlit as st
import zipfile
import pandas as pd
import pytesseract # Asegúrate de tener Tesseract OCR instalado en tu sistema
import fitz  # PyMuPDF
import docx
import io
import json
from PIL import Image
from lingua import Language, LanguageDetectorBuilder

# === Idiomas soportados (como en tu código) ===
IDIOMAS_OBJETIVO = [
    Language.SPANISH,
    Language.ENGLISH,
    Language.FRENCH,
    Language.GERMAN
]
try:
    detector = LanguageDetectorBuilder.from_languages(*IDIOMAS_OBJETIVO).build()
except Exception as e:
    st.error(f"Error al inicializar el detector de idioma: {e}. La detección de idioma podría no funcionar.")
    # Fallback a un detector nulo
    class DetectorNulo:
        def detect_language_of(self, text): return None
    detector = DetectorNulo()

# === Funciones para leer cada tipo de archivo ===
# Optimizadas para manejar correctamente los UploadedFile de Streamlit

def leer_txt(archivo_subido):
    archivo_subido.seek(0)
    return archivo_subido.read().decode("utf-8", errors="replace")

def leer_pdf(archivo_subido):
    archivo_subido.seek(0)
    contenido_bytes = archivo_subido.read()
    texto_pdf = ""
    try:
        with fitz.open(stream=contenido_bytes, filetype="pdf") as doc_pdf:
            for pagina in doc_pdf:
                texto_pdf += pagina.get_text() + "\n"
    except Exception as e:
        st.warning(f"No se pudo procesar '{archivo_subido.name}' como PDF estándar: {e}.")
    return texto_pdf

def leer_docx(archivo_subido):
    archivo_subido.seek(0)
    try:
        documento_docx = docx.Document(io.BytesIO(archivo_subido.read()))
        return "\n".join([parrafo.text for parrafo in documento_docx.paragraphs])
    except Exception as e:
        st.error(f"Error al leer DOCX '{archivo_subido.name}': {e}")
        return ""

def leer_excel(archivo_subido):
    archivo_subido.seek(0)
    try:
        dataframe_excel = pd.read_excel(io.BytesIO(archivo_subido.read()))
        return dataframe_excel.to_string()
    except Exception as e:
        st.error(f"Error al leer Excel '{archivo_subido.name}': {e}")
        return ""

def leer_csv(archivo_subido):
    archivo_subido.seek(0)
    try:
        # Intentar con UTF-8, luego con latin1 como fallback
        try:
            contenido_decodificado = archivo_subido.read().decode('utf-8')
        except UnicodeDecodeError:
            archivo_subido.seek(0) # Rebobinar para el siguiente intento
            contenido_decodificado = archivo_subido.read().decode('latin1')
        dataframe_csv = pd.read_csv(io.StringIO(contenido_decodificado))
        return dataframe_csv.to_string()
    except Exception as e:
        st.error(f"Error al leer CSV '{archivo_subido.name}': {e}")
        return ""

def leer_json(archivo_subido): # Nombre de tu función original
    archivo_subido.seek(0)
    try:
        datos_json = json.load(archivo_subido)
        return json.dumps(datos_json, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo JSON '{archivo_subido.name}': {e}")
        return f"Error al procesar JSON: {e}" # Devolver el error como string para el contexto

def leer_imagen(archivo_subido): # Nombre de tu función original
    archivo_subido.seek(0)
    try:
        imagen_pil = Image.open(io.BytesIO(archivo_subido.read()))
        return pytesseract.image_to_string(imagen_pil)
    except Exception as e:
        if "Tesseract is not installed" in str(e) or isinstance(e, FileNotFoundError): # Ser más específico
            st.error("Error de OCR: Tesseract no está instalado o no se encuentra en el PATH.")
        else:
            st.error(f"❌ Error al procesar imagen '{archivo_subido.name}' con OCR: {e}")
        return ""

def leer_zip(archivo_subido): # Nombre de tu función original
    archivo_subido.seek(0)
    texto_agregado_zip = ""
    try:
        with zipfile.ZipFile(archivo_subido, 'r') as archivo_zip_abierto:
            for nombre_interno_zip in archivo_zip_abierto.namelist():
                if nombre_interno_zip.endswith('/') or nombre_interno_zip.startswith('__MACOSX/'):
                    continue
                with archivo_zip_abierto.open(nombre_interno_zip) as archivo_en_zip:
                    bytes_archivo_zip = archivo_en_zip.read()
                    stream_bytes_zip = io.BytesIO(bytes_archivo_zip)
                    stream_bytes_zip.name = nombre_interno_zip # Algunas funciones de lectura podrían usar .name

                    nombre_interno_lower_zip = nombre_interno_zip.lower()
                    contenido_item_actual_zip = ""

                    if nombre_interno_lower_zip.endswith(".txt"):
                        contenido_item_actual_zip = bytes_archivo_zip.decode("utf-8", errors="replace")
                    elif nombre_interno_lower_zip.endswith(".docx"):
                        contenido_item_actual_zip = leer_docx(stream_bytes_zip)
                    elif nombre_interno_lower_zip.endswith(".csv"):
                        contenido_item_actual_zip = leer_csv(stream_bytes_zip)
                    elif nombre_interno_lower_zip.endswith(".xlsx"):
                        contenido_item_actual_zip = leer_excel(stream_bytes_zip)
                    elif nombre_interno_lower_zip.endswith(".pdf"):
                        contenido_item_actual_zip = leer_pdf(stream_bytes_zip)
                    elif nombre_interno_lower_zip.endswith(".json"):
                        contenido_item_actual_zip = leer_json(stream_bytes_zip)
                    
                    if contenido_item_actual_zip:
                        texto_agregado_zip += f"\n\n--- Contenido de: {nombre_interno_zip} (dentro de {archivo_subido.name}) ---\n{contenido_item_actual_zip}"
        return texto_agregado_zip
    except zipfile.BadZipFile:
        st.error(f"Error: El archivo '{archivo_subido.name}' no es un ZIP válido o está corrupto.")
        return ""
    except Exception as e_zip_proc:
        st.error(f"Error al procesar archivo ZIP '{archivo_subido.name}': {e_zip_proc}")
        return ""

# === Procesamiento de Archivos Subidos (como en tu código, con el añadido del flag) ===
def procesar_archivo_subido():
    # El título "Subir archivo para análisis" se puede poner en el expander del módulo que llama.
    archivos = st.file_uploader(
        "Arrastra archivos o haz clic para buscar. El contenido se usará como contexto en el chat.",
        type=["txt", "pdf", "docx", "xlsx", "csv", "json", "zip", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="uploader_analizador_archivos_v4" # Key única para el widget
    )

    textos_extraidos = []
    archivos_procesados_ok_nombres = [] # Nombres de archivos procesados exitosamente

    if archivos: # Si el usuario ha subido archivos
        with st.spinner("🔄 Analizando archivos... Por favor, espera."):
            for archivo_para_procesar in archivos:
                try:
                    nombre_archivo_lower = archivo_para_procesar.name.lower()
                    contenido_actual_item = ""
                    if nombre_archivo_lower.endswith(".txt"):
                        contenido_actual_item = leer_txt(archivo_para_procesar)
                    elif nombre_archivo_lower.endswith(".pdf"):
                        contenido_actual_item = leer_pdf(archivo_para_procesar)
                    elif nombre_archivo_lower.endswith(".docx"):
                        contenido_actual_item = leer_docx(archivo_para_procesar)
                    elif nombre_archivo_lower.endswith(".xlsx"):
                        contenido_actual_item = leer_excel(archivo_para_procesar)
                    elif nombre_archivo_lower.endswith(".csv"):
                        contenido_actual_item = leer_csv(archivo_para_procesar)
                    elif nombre_archivo_lower.endswith(".json"):
                        contenido_actual_item = leer_json(archivo_para_procesar) # Usando tu nombre de función
                    elif nombre_archivo_lower.endswith((".jpg", ".jpeg", ".png")):
                        contenido_actual_item = leer_imagen(archivo_para_procesar) # Usando tu nombre de función
                    elif nombre_archivo_lower.endswith(".zip"):
                        contenido_actual_item = leer_zip(archivo_para_procesar) # Usando tu nombre de función
                    else:
                        st.warning(f"⚠️ Tipo de archivo no compatible: {archivo_para_procesar.name}")
                        continue # Saltar al siguiente archivo
                    
                    if contenido_actual_item: # Solo añadir si se extrajo algo
                        textos_extraidos.append(f"--- Inicio del contenido del archivo: {archivo_para_procesar.name} ---\n{contenido_actual_item}\n--- Fin del contenido del archivo: {archivo_para_procesar.name} ---")
                        archivos_procesados_ok_nombres.append(archivo_para_procesar.name)

                except Exception as e_procesamiento:
                    st.error(f"❌ Error crítico al procesar el archivo `{archivo_para_procesar.name}`: {e_procesamiento}")

    # Añadir al contexto si hay contenido (como en tu código)
    if textos_extraidos:
        contexto_total_agregado = "\n\n".join(textos_extraidos)
        
        # Detección de idioma del contexto combinado (como en tu código)
        idioma_detectado_obj = detector.detect_language_of(contexto_total_agregado[:1000]) # Analizar primeros 1000 chars para eficiencia
        idioma_nombre_str = idioma_detectado_obj.name.lower() if idioma_detectado_obj else "unknown"

        instrucciones_contexto = { # Como en tu código
            "spanish": "El usuario ha subido uno o más archivos para analizar. A continuación tienes el contenido extraído. Úsalo como contexto para responder.",
            "english": "The user has uploaded one or more files for analysis. Below is the extracted content. Use it as context for your responses.",
            "french": "L'utilisateur a téléchargé un ou plusieurs fichiers à analyser. Voici le contenu extrait. Utilisez-le comme contexte pour vos réponses.",
            "german": "Der Benutzer hat eine oder mehrere Dateien zur Analyse hochgeladen. Verwenden Sie den folgenden Inhalt als Kontext.",
            "unknown": "The user uploaded files. Use the following extracted text as reference context."
        }

        mensaje_sistema_para_contexto = instrucciones_contexto.get(idioma_nombre_str, instrucciones_contexto["unknown"])
        
        # Guardar el contexto completo (instrucción + contenido) en st.session_state
        # Esta es la clave que tu chat_libre_module.py espera.
        st.session_state.archivo_contexto = f"{mensaje_sistema_para_contexto}\n\n--- INICIO DEL CONTENIDO DE ARCHIVOS ---\n{contexto_total_agregado}\n--- FIN DEL CONTENIDO DE ARCHIVOS ---"
        
        nombres_display_str = ", ".join(archivos_procesados_ok_nombres)
        st.success(f"✅ Archivo(s) analizado(s): **{nombres_display_str}**. Su contenido se ha añadido al contexto del chat.")
        
        # --- ¡CAMBIO IMPORTANTE AQUÍ! ---
        # Indicar al módulo que llama (chat_libre_module) que el uploader debería colapsarse.
        st.session_state.chat_libre_archivo_procesado_y_colapsar = True
        # ---------------------------------
