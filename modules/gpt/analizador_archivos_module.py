import streamlit as st
import zipfile
import pandas as pd
import pytesseract
import fitz  # PyMuPDF
import docx
import io
from PIL import Image


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
    return texto


# === Procesamiento silencioso y automático ===

def procesar_archivo_subido():
    st.markdown("### 📁 Subir archivo para análisis")
    archivos = st.file_uploader(
        "Tipos permitidos: txt, pdf, docx, xlsx, csv, zip, imágenes",
        type=["txt", "pdf", "docx", "xlsx", "csv", "zip", "jpg", "jpeg", "png"],
        accept_multiple_files=True
    )

    textos_extraidos = []

    if archivos:
        with st.spinner("🔄 Analizando archivos..."):
            for archivo in archivos:
                try:
                    if archivo.name.endswith(".txt"):
                        textos_extraidos.append(leer_txt(archivo))
                    elif archivo.name.endswith(".pdf"):
                        textos_extraidos.append(leer_pdf(archivo))
                    elif archivo.name.endswith(".docx"):
                        textos_extraidos.append(leer_docx(archivo))
                    elif archivo.name.endswith(".xlsx"):
                        textos_extraidos.append(leer_excel(archivo))
                    elif archivo.name.endswith(".csv"):
                        textos_extraidos.append(leer_csv(archivo))
                    elif archivo.name.endswith((".jpg", ".jpeg", ".png")):
                        textos_extraidos.append(leer_imagen(archivo))
                    elif archivo.name.endswith(".zip"):
                        textos_extraidos.append(leer_zip(archivo))
                    else:
                        st.warning(f"❌ Tipo de archivo no compatible: {archivo.name}")
                except Exception as e:
                    st.error(f"❌ Error al procesar `{archivo.name}`: {e}")

    # Guardar el contexto como mensaje system
    if textos_extraidos:
        contexto_total = "\n\n".join(textos_extraidos)
        st.session_state.archivo_contexto = (
            "El usuario ha subido uno o más archivos o imágenes para análisis. "
            "Aquí tienes el texto extraído que debes tener en cuenta en todas tus respuestas:\n\n"
            f"{contexto_total}"
        )
        st.success(f"✅ {len(textos_extraidos)} archivo(s) analizado(s) y añadido(s) al contexto.")
