import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
from drive_utils import (
    obtener_proyectos_drive,
    listar_archivos_en_carpeta,
    descargar_archivo_de_drive
)

def render_scraping_etiquetas_url():
    st.title("🧬 Extraer etiquetas de URLs desde archivo JSON")
    st.markdown("📁 **Sube un archivo JSON con URLs obtenidas de Google**")

    # Obtener proyectos y seleccionar
    CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"
    proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)

    if not proyectos:
        st.error("❌ No se encontraron carpetas en Drive.")
        return

    nombre_proyecto = st.sidebar.selectbox("Seleccione proyecto:", list(proyectos.keys()), key="etiqueta_proyecto")
    carpeta_id = proyectos[nombre_proyecto]

    # Fuente del archivo
    fuente = st.radio("Selecciona fuente del archivo:", ["Desde ordenador", "Desde Drive"], horizontal=True)

    json_content = None
    archivo_drive = None

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📂 Sube archivo JSON", type="json")
        if archivo:
            json_content = archivo.read()
    else:
        archivos_drive = listar_archivos_en_carpeta(carpeta_id)
        if archivos_drive:
            seleccion_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_drive.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                file_id = archivos_drive[seleccion_drive]
                json_content = descargar_archivo_de_drive(file_id)
                archivo_drive = seleccion_drive
        else:
            st.warning("⚠️ No se encontraron archivos JSON en esta carpeta.")

    if json_content:
        nombre_mostrado = archivo.name if fuente == "Desde ordenador" else archivo_drive
        st.success(f"✅ Archivo cargado: {nombre_mostrado}")

        st.markdown("### 🏷️ Etiquetas a extraer")
        col1, col2, col3, col4 = st.columns(4)
        etiquetas = []
        if col1.checkbox("title", key="e_title"): etiquetas.append("title")
        if col2.checkbox("H1", key="e_h1"): etiquetas.append("h1")
        if col3.checkbox("H2", key="e_h2"): etiquetas.append("h2")
        if col4.checkbox("H3", key="e_h3"): etiquetas.append("h3")

        if etiquetas:
            if st.button("🔍 Extraer etiquetas"):
                try:
                    data = json.loads(json_content)
                    resultados = []

                    for grupo in data:
                        busqueda = grupo.get("busqueda", "")
                        for entrada in grupo.get("urls", []):
                            url = entrada.get("url")
                            try:
                                res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                                soup = BeautifulSoup(res.text, 'html.parser')
                                result = {"url": url, "busqueda": busqueda}

                                if "title" in etiquetas:
                                    result["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
                                for tag in ["h1", "h2", "h3"]:
                                    if tag in etiquetas:
                                        result[tag] = [h.text.strip() for h in soup.find_all(tag)]

                                resultados.append(result)
                            except Exception as e:
                                resultados.append({"url": url, "error": str(e)})

                    st.subheader("📦 Resultados con etiquetas extraídas")
                    st.json(resultados)

                    nombre_final = "etiquetas_extraidas.json"
                    json_bytes = json.dumps(resultados, ensure_ascii=False, indent=2).encode('utf-8')
                    st.download_button("⬇️ Descargar JSON", data=json_bytes, file_name=nombre_final, mime="application/json")

                except Exception as e:
                    st.error(f"❌ Error al procesar el archivo: {e}")
        else:
            st.info("☝️ Selecciona al menos una etiqueta para extraer.")

