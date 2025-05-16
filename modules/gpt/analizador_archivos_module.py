import streamlit as st
import zipfile
import pandas as pd
import pytesseract
import fitz  # PyMuPDF
import docx
import io
from PIL import Image


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


def procesar_archivo_subido():
    st.markdown("### 📁 Subir archivo para análisis")
    archivo = st.file_uploader(
        "Tipos permitidos: txt, pdf, docx, xlsx, csv, zip, imágenes",
        type=["txt", "pdf", "docx", "xlsx", "csv", "zip", "jpg", "jpeg", "png"]
    )

    texto_extraido = ""
    if archivo:
        st.info(f"Procesando: `{archivo.name}`")
        try:
            if archivo.name.endswith(".txt"):
                texto_extraido = leer_txt(archivo)
            elif archivo.name.endswith(".pdf"):
                texto_extraido = leer_pdf(archivo)
            elif archivo.name.endswith(".docx"):
                texto_extraido = leer_docx(archivo)
            elif archivo.name.endswith(".xlsx"):
                texto_extraido = leer_excel(archivo)
            elif archivo.name.endswith(".csv"):
                texto_extraido = leer_csv(archivo)
            elif archivo.name.endswith((".jpg", ".jpeg", ".png")):
                texto_extraido = leer_imagen(archivo)
            elif archivo.name.endswith(".zip"):
                texto_extraido = leer_zip(archivo)
            else:
                st.warning("❌ Tipo de archivo no compatible.")
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")

    if texto_extraido:
        with st.expander("📄 Ver texto extraído del archivo"):
            st.text_area("Contenido procesado:", value=texto_extraido, height=300)

        # Agregar automáticamente como contexto del sistema
        st.session_state.archivo_contexto = (
            "El usuario ha subido un archivo o imagen para análisis. "
            "Este es el texto extraído que debes tener en cuenta en todas tus respuestas:\n\n"
            f"{texto_extraido}"
        )
        st.success("✅ El contenido del archivo se ha añadido automáticamente como contexto del sistema.")

    return texto_extraido
