# modules/gpt/analizador_archivos_module.py
import streamlit as st
import zipfile
import pandas as pd
import pytesseract # Asegúrate de tener Tesseract OCR instalado
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
detector = LanguageDetectorBuilder.from_languages(*IDIOMAS_OBJETIVO).build()

# === Funciones para leer cada tipo de archivo (como en tu código) ===
# (Asegúrate de que estas funciones manejen bien los 'file-like objects' de Streamlit,
# especialmente después de leerlos una vez, usando file.seek(0) si es necesario
# o leyendo en bytes y usando io.BytesIO para las librerías que lo requieran)

def leer_txt(file):
    file.seek(0)
    return file.read().decode("utf-8", errors="replace")

def leer_pdf(file):
    file.seek(0)
    doc = fitz.open(stream=file.read(), filetype="pdf")
    texto = "\n".join([page.get_text() for page in doc])
    doc.close()
    return texto

def leer_docx(file):
    file.seek(0)
    # python-docx necesita un stream de bytes o una ruta.
    doc = docx.Document(io.BytesIO(file.read()))
    return "\n".join([p.text for p in doc.paragraphs])

def leer_excel(file):
    file.seek(0)
    df = pd.read_excel(io.BytesIO(file.read())) # pandas puede necesitar BytesIO para algunos formatos desde un stream
    return df.to_string()

def leer_csv(file):
    file.seek(0)
    try:
        content = file.read().decode('utf-8')
    except UnicodeDecodeError:
        file.seek(0)
        content = file.read().decode('latin-1') # Fallback
    df = pd.read_csv(io.StringIO(content))
    return df.to_string()

def leer_json(file): # Renombrado en tu código original, lo mantengo
    file.seek(0)
    try:
        data = json.load(file) # json.load toma un objeto archivo
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"❌ Error al leer JSON: {e}"

def leer_imagen(file): # Renombrado en tu código original, lo mantengo
    file.seek(0)
    image = Image.open(io.BytesIO(file.read()))
    return pytesseract.image_to_string(image)

def leer_zip(file): # Renombrado en tu código original, lo mantengo
    file.seek(0)
    texto_completo_zip = ""
    try:
        with zipfile.ZipFile(file, 'r') as z:
            for name_in_zip in z.namelist():
                if name_in_zip.endswith('/') or name_in_zip.startswith('__MACOSX/'):
                    continue
                with z.open(name_in_zip) as f_in_zip:
                    bytes_internos = f_in_zip.read()
                    archivo_bytes_io = io.BytesIO(bytes_internos)
                    archivo_bytes_io.name = name_in_zip # Algunas funciones de lectura podrían necesitar .name

                    nombre_lower_in_zip = name_in_zip.lower()
                    contenido_item_zip = ""
                    if nombre_lower_in_zip.endswith(".txt"):
                        contenido_item_zip = bytes_internos.decode("utf-8", errors="replace")
                    elif nombre_lower_in_zip.endswith(".docx"):
                        contenido_item_zip = leer_docx(archivo_bytes_io)
                    elif nombre_lower_in_zip.endswith(".csv"):
                        contenido_item_zip = leer_csv(archivo_bytes_io)
                    elif nombre_lower_in_zip.endswith(".xlsx"):
                        contenido_item_zip = leer_excel(archivo_bytes_io)
                    elif nombre_lower_in_zip.endswith(".pdf"):
                        contenido_item_zip = leer_pdf(archivo_bytes_io)
                    elif nombre_lower_in_zip.endswith(".json"):
                        contenido_item_zip = leer_json(archivo_bytes_io)
                    
                    if contenido_item_zip:
                        texto_completo_zip += f"\n\n--- Contenido de: {name_in_zip} ---\n{contenido_item_zip}"
        return texto_completo_zip
    except zipfile.BadZipFile:
        st.error(f"Error: El archivo '{file.name}' no es un ZIP válido o está corrupto.")
        return ""
    except Exception as e_zip:
        st.error(f"Error al procesar archivo ZIP '{file.name}': {e_zip}")
        return ""


# === Procesamiento (como en tu código, con el añadido del flag) ===
def procesar_archivo_subido():
    # El título "Subir archivo para análisis" se mostrará en el expander del módulo de chat.
    # Aquí solo el file_uploader.
    archivos = st.file_uploader(
        "Arrastra archivos aquí o haz clic para buscar. El contenido se usará como contexto.",
        type=["txt", "pdf", "docx", "xlsx", "csv", "json", "zip", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="uploader_en_analizador_chat_libre" # Key única
    )

    textos_extraidos = []
    archivos_procesados_con_exito = 0

    if archivos:
        with st.spinner("🔄 Analizando archivos..."):
            for archivo_individual in archivos:
                try:
                    nombre_lower = archivo_individual.name.lower()
                    contenido_item = ""
                    if nombre_lower.endswith(".txt"):
                        contenido_item = leer_txt(archivo_individual)
                    elif nombre_lower.endswith(".pdf"):
                        contenido_item = leer_pdf(archivo_individual)
                    elif nombre_lower.endswith(".docx"):
                        contenido_item = leer_docx(archivo_individual)
                    # ... (resto de tus elif para xlsx, csv, json, imágenes, zip) ...
                    elif nombre_lower.endswith(".xlsx"):
                        contenido_item = leer_excel(archivo_individual)
                    elif nombre_lower.endswith(".csv"):
                        contenido_item = leer_csv(archivo_individual)
                    elif nombre_lower.endswith(".json"):
                        contenido_item = leer_json(archivo_individual) # Usando tu nombre de función
                    elif nombre_lower.endswith((".jpg", ".jpeg", ".png")):
                        contenido_item = leer_imagen(archivo_individual) # Usando tu nombre de función
                    elif nombre_lower.endswith(".zip"):
                        contenido_item = leer_zip(archivo_individual) # Usando tu nombre de función
                    else:
                        st.warning(f"⚠️ Tipo de archivo no compatible: {archivo_individual.name}")
                        continue
                    
                    if contenido_item:
                        textos_extraidos.append(f"--- Inicio del contenido de: {archivo_individual.name} ---\n{contenido_item}\n--- Fin del contenido de: {archivo_individual.name} ---")
                        archivos_procesados_con_exito +=1
                except Exception as e:
                    st.error(f"❌ Error al procesar `{archivo_individual.name}`: {e}")

    # Añadir al contexto si hay contenido (como en tu código)
    if textos_extraidos:
        contexto_total = "\n\n".join(textos_extraidos)
        idioma_detectado = detector.detect_language_of(contexto_total[:1000]) # Analizar una porción para eficiencia
        idioma = idioma_detectado.name.lower() if idioma_detectado else "unknown"

        instrucciones = {
            "spanish": "El usuario ha subido uno o más archivos para analizar. A continuación tienes el contenido extraído. Úsalo como contexto para responder.",
            "english": "The user has uploaded one or more files for analysis. Below is the extracted content. Use it as context for your responses.",
            "french": "L'utilisateur a téléchargé un ou plusieurs fichiers à analyser. Voici le contenu extrait. Utilisez-le comme contexte pour vos réponses.",
            "german": "Der Benutzer hat eine oder mehrere Dateien zur Analyse hochgeladen. Verwenden Sie den folgenden Inhalt als Kontext.",
            "unknown": "The user uploaded files. Use the following extracted text as reference context."
        }

        mensaje_contexto = instrucciones.get(idioma, instrucciones["unknown"]) + "\n\n" + contexto_total
        st.session_state.archivo_contexto = mensaje_contexto # Esta es la clave que usa tu chat_libre_module
        st.success(f"✅ {archivos_procesados_con_exito} archivo(s) analizado(s) y añadido(s) al contexto.")
        
        # --- ¡CAMBIO IMPORTANTE AQUÍ! ---
        # Indicar al módulo que llama (chat_libre_module) que el uploader debería colapsarse.
        st.session_state.chat_libre_archivo_procesado_y_colapsar = True
        # ---------------------------------
