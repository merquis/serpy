import json
import streamlit as st
from drive_utils import obtener_proyectos_drive, listar_archivos_en_carpeta, descargar_archivo_de_drive
from bs4 import BeautifulSoup
import requests

# ════════════════════════════════════════════════
# 🎯 MÓDULO: Extraer etiquetas desde archivo JSON
# ════════════════════════════════════════════════

CARPETA_SERPY_ID = "1iIDxBzyeeVYJD4JksZdFNnUNLoW7psKy"


def render_scraping_etiquetas_url():
    st.title("🧬 Extraer etiquetas de URLs desde archivo JSON")
    st.markdown("### 📁 Sube un archivo JSON con URLs obtenidas de Google")

    # Fuente del archivo: ordenador o Drive
    fuente = st.radio("Selecciona fuente del archivo:", ["Desde ordenador", "Desde Drive"], horizontal=True)

    contenido = None
    nombre_archivo = None

    if fuente == "Desde ordenador":
        archivo_subido = st.file_uploader("Sube archivo JSON", type="json")
        if archivo_subido:
            contenido = archivo_subido.read()
            nombre_archivo = archivo_subido.name

    else:
        proyectos = obtener_proyectos_drive(CARPETA_SERPY_ID)
        if not proyectos:
            st.error("❌ No se encontraron proyectos en Drive")
            return

        proyecto_seleccionado = st.selectbox("Selecciona un proyecto:", list(proyectos.keys()))
        archivos_json = listar_archivos_en_carpeta(proyectos[proyecto_seleccionado])

        if archivos_json:
            archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos_json.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                contenido = descargar_archivo_de_drive(archivos_json[archivo_drive])
                nombre_archivo = archivo_drive
        else:
            st.warning("⚠️ No hay archivos JSON en este proyecto.")

    if contenido:
        st.success(f"✅ Archivo cargado: {nombre_archivo}")

        try:
            datos_json = json.loads(contenido)
            todas_urls = []
            for entrada in datos_json:
                urls = entrada.get("urls", [])
                for item in urls:
                    url = item.get("url")
                    if url:
                        todas_urls.append(url)

            if not todas_urls:
                st.warning("⚠️ No se encontraron URLs en el archivo JSON")
                return

            # Etiquetas a extraer (checkboxes)
            st.markdown("### 🏷️ Etiquetas a extraer")
            etiquetas = []
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.checkbox("title", key="etiqueta_title"): etiquetas.append("title")
            with col2:
                if st.checkbox("H1", key="etiqueta_h1"): etiquetas.append("h1")
            with col3:
                if st.checkbox("H2", key="etiqueta_h2"): etiquetas.append("h2")
            with col4:
                if st.checkbox("H3", key="etiqueta_h3"): etiquetas.append("h3")

            if not etiquetas:
                st.info("ℹ️ Selecciona al menos una etiqueta para extraer.")
                return

            # Botón para procesar
            if st.button("🔎 Extraer etiquetas"):
                resultados = []
                for url in todas_urls:
                    try:
                        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                        soup = BeautifulSoup(r.text, "html.parser")
                        info = {"url": url}

                        if "title" in etiquetas:
                            info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
                        if "h1" in etiquetas:
                            info["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")]
                        if "h2" in etiquetas:
                            info["h2"] = [h.get_text(strip=True) for h in soup.find_all("h2")]
                        if "h3" in etiquetas:
                            info["h3"] = [h.get_text(strip=True) for h in soup.find_all("h3")]

                        resultados.append(info)
                    except Exception as e:
                        resultados.append({"url": url, "error": str(e)})

                st.subheader("📦 Resultados obtenidos")
                st.json(resultados)

                nombre_salida = "etiquetas_extraidas.json"
                st.download_button(
                    label="⬇️ Descargar JSON",
                    data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
                    file_name=nombre_salida,
                    mime="application/json"
                )

        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")
