import streamlit as st
import zipfile
import pandas as pd
import pytesseract
import fitz  # PyMuPDF
import docx
import io
import json
from PIL import Image
from langdetect import detect


# === Funciones para leer cada tipo de archivo ===

def leer_txt(file):
    return file.read().decode("utf-8")


def leer_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    texto = "\n".join([page.get_text() for page in doc])
    doc.close()
    return texto


def leer_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])


def leer_excel(file):
    df = pd.read_excel(file)
    return df.to_string()


def leer_csv(file):
    df = pd.read_csv(file)
    return df.to_string()


def leer_json(file):
    try:
        data = json.load(file)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"❌ Error al leer JSON: {e}"


def leer_imagen(file):
    image = Image.open(file)
    return pytesseract.image_to_string(image)


def leer_zip(file):
    texto = ""
    with zipfile.ZipFile(file) as z:
        for name in z.namelist():
            with z.open(name) as f:
                if name.endswith(".txt"):
                    texto += f"\n\n--- {name} ---\n" + f.read().decode("utf-8")
                elif name.endswith(".docx"):
                    texto += f"\n\n--- {name} ---\n" + leer_docx(f)
                elif name.endswith(".csv"):
                    texto += f"\n\n--- {name} ---\n" + pd.read_csv(f).to_string()
                elif name.endswith(".xlsx"):
                    texto += f"\n\n--- {name} ---\n" + pd.read_excel(f).to_string()
                elif name.endswith(".pdf"):
                    texto += f"\n\n--- {name} ---\n" + leer_pdf(f)
                elif name.endswith(".json"):
                    texto += f"\n\n--- {name} ---\n" + leer_json(f)
    return texto


# === Procesamiento silencioso con contexto automático ===

def procesar_archivo_subido():
    st.markdown("### 📁 Subir archivo para análisis")
    archivos = st.file_uploader(
        "Tipos permitidos: txt, pdf, docx, xlsx, csv, json, zip, imágenes",
        type=["txt", "pdf", "docx", "xlsx", "csv", "json", "zip", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    textos_extraidos = []

    if archivos:
        with st.spinner("🔄 Analizando archivos..."):
            for archivo in archivos:
                try:
                    nombre = archivo.name.lower()
                    if nombre.endswith(".txt"):
                        textos_extraidos.append(leer_txt(archivo))
                    elif nombre.endswith(".pdf"):
                        textos_extraidos.append(leer_pdf(archivo))
                    elif nombre.endswith(".docx"):
                        textos_extraidos.append(leer_docx(archivo))
                    elif nombre.endswith(".xlsx"):
                        textos_extraidos.append(leer_excel(archivo))
                    elif nombre.endswith(".csv"):
                        textos_extraidos.append(leer_csv(archivo))
                    elif nombre.endswith(".json"):
                        textos_extraidos.append(leer_json(archivo))
                    elif nombre.endswith((".jpg", ".jpeg", ".png")):
                        textos_extraidos.append(leer_imagen(archivo))
                    elif nombre.endswith(".zip"):
                        textos_extraidos.append(leer_zip(archivo))
                    else:
                        st.warning(f"❌ Tipo de archivo no compatible: {archivo.name}")
                except Exception as e:
                    st.error(f"❌ Error al procesar `{archivo.name}`: {e}")

    # Añadir al contexto si hay contenido
    if textos_extraidos:
        contexto_total = "\n\n".join(textos_extraidos)
        try:
            idioma = detect(contexto_total)
        except Exception:
            idioma = "unknown"

        instrucciones = {
            "es": "El usuario ha subido uno o más archivos para analizar. A continuación tienes el contenido extraído. Úsalo como contexto para responder.",
            "en": "The user has uploaded one or more files for analysis. Below is the extracted content. Use it as context for your responses.",
            "fr": "L'utilisateur a téléchargé un ou plusieurs fichiers à analyser. Voici le contenu extrait. Utilisez-le comme contexte pour vos réponses.",
            "unknown": "The user uploaded files. Use the following extracted text as reference context."
        }

        mensaje_contexto = instrucciones.get(idioma, instrucciones["unknown"]) + "\n\n" + contexto_total
        st.session_state.archivo_contexto = mensaje_contexto
        st.success(f"✅ {len(textos_extraidos)} archivo(s) analizado(s) y añadido(s) al contexto.")
