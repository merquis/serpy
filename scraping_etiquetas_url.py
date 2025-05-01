import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
from drive_utils import listar_archivos_en_carpeta, descargar_archivo_de_drive

def extraer_etiquetas_de_urls(data, etiquetas):
    resultados = []
    for bloque in data:
        busqueda = bloque.get("busqueda", "")
        urls = bloque.get("urls", [])
        urls_extraidas = []

        for url in urls:
            resultado = {"url": url}
            try:
                res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(res.text, 'html.parser')

                if "title" in etiquetas:
                    resultado["title"] = soup.title.string.strip() if soup.title and soup.title.string else None

                for tag in ["h1", "h2", "h3"]:
                    if tag in etiquetas:
                        resultado[tag] = [h.text.strip() for h in soup.find_all(tag)]

                urls_extraidas.append(resultado)

            except Exception as e:
                urls_extraidas.append({"url": url, "error": str(e)})

        resultados.append({
            "busqueda": busqueda,
            "resultados": urls_extraidas
        })

    return resultados

def render_scraping_etiquetas_url():
    st.title("🧬 Extraer etiquetas de URLs desde archivo JSON")
    st.markdown("📁 **Sube un archivo JSON con URLs obtenidas de Google**")

    # Opción de fuente: Drive o archivo local
    fuente = st.radio("Seleccionar fuente del archivo:", ["📂 Desde ordenador", "📁 Desde Drive"])

    contenido_json = None
    nombre_origen = None

    if fuente == "📂 Desde ordenador":
        archivo = st.file_uploader("Sube tu archivo JSON", type="json")
        if archivo:
            try:
                contenido_json = json.load(archivo)
                nombre_origen = archivo.name
            except Exception as e:
                st.error(f"❌ Error al leer el archivo: {e}")

    elif fuente == "📁 Desde Drive":
        if 'proyecto_id' in st.session_state:
            archivos_drive = listar_archivos_en_carpeta(st.session_state.proyecto_id, extension=".json")
            if archivos_drive:
                seleccionado = st.selectbox("Selecciona un archivo de Drive", list(archivos_drive.keys()))
                if st.button("📥 Cargar archivo de Drive"):
                    contenido_json = descargar_archivo_de_drive(archivos_drive[seleccionado])
                    nombre_origen = seleccionado
            else:
                st.warning("⚠️ No se encontraron archivos JSON en la carpeta del proyecto.")
        else:
            st.warning("⚠️ No se ha definido un proyecto.")

    if contenido_json:
        st.success(f"✅ Archivo cargado: {nombre_origen}")

        # Opciones de etiquetas a extraer
        st.markdown("### 🏷️ Etiquetas a extraer")
        col1, col2, col3, col4 = st.columns(4)
        etiquetas = []
        if col1.checkbox("title", value=True): etiquetas.append("title")
        if col2.checkbox("H1"): etiquetas.append("h1")
        if col3.checkbox("H2"): etiquetas.append("h2")
        if col4.checkbox("H3"): etiquetas.append("h3")

        if st.button("🧪 Extraer etiquetas"):
            with st.spinner("Extrayendo etiquetas..."):
                resultado_final = extraer_etiquetas_de_urls(contenido_json, etiquetas)
                st.json(resultado_final)
