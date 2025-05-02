import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
from scraper_tags_common import scrape_tags_from_url, seleccionar_etiquetas_html
from drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive, subir_json_a_drive

def render_scraping_etiquetas_url():
    st.title("🧬 Scrapear etiquetas desde archivo JSON")

    fuente = st.radio("Selecciona la fuente del archivo:", ["Desde ordenador", "Desde Drive"], horizontal=True)

    contenido = None
    nombre_archivo = ""

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("Sube tu archivo JSON con URLs", type="json")
        if archivo:
            contenido = archivo.read()
            nombre_archivo = archivo.name
    else:
        if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
            st.warning("⚠️ Debes seleccionar un proyecto antes.")
            return

        archivos = listar_archivos_en_carpeta(st.session_state.proyecto_id)
        if not archivos:
            st.info("No hay archivos JSON en la carpeta del proyecto.")
            return

        archivo_drive = st.selectbox("Selecciona un archivo de Drive", list(archivos.keys()))
        if st.button("📥 Cargar archivo seleccionado"):
            contenido = obtener_contenido_archivo_drive(archivos[archivo_drive])
            nombre_archivo = archivo_drive

    if contenido:
        try:
            datos = json.loads(contenido)
        except Exception as e:
            st.error(f"❌ Error al cargar JSON: {e}")
            return

        urls = []
        for entrada in datos:
            urls += entrada.get("urls", [])

        etiquetas = seleccionar_etiquetas_html()

        if st.button("🔎 Iniciar scraping"):
            resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]
            st.subheader("📦 Resultados")
            st.json(resultados)

            json_resultado = json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8")

            st.download_button("⬇️ Descargar JSON", data=json_resultado, file_name="resultados_scraping.json", mime="application/json")

            if st.button("📤 Subir resultados a Google Drive"):
                if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
                    enlace = subir_json_a_drive("resultados_scraping.json", json_resultado, st.session_state.proyecto_id)
                    if enlace:
                        st.success(f"✅ Subido a Drive: [Ver archivo]({enlace})")
                else:
                    st.error("❌ No se detectó proyecto activo.")

def render_scraping_urls_manuales():
    st.title("✍️ Scrapear URLs manualmente")
    entrada = st.text_area("🔗 Pega una o varias URLs (una por línea)", height=200)
    if not entrada.strip():
        return

    etiquetas = seleccionar_etiquetas_html()
    urls = [u.strip() for u in entrada.splitlines() if u.strip()]

    if st.button("🔎 Iniciar scraping"):
        resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]
        st.subheader("📦 Resultados")
        st.json(resultados)

        json_resultado = json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8")
        st.download_button("⬇️ Descargar JSON", data=json_resultado, file_name="manual_scraping.json", mime="application/json")

        if st.button("📤 Subir a Google Drive"):
            if "proyecto_id" in st.session_state and st.session_state.proyecto_id:
                enlace = subir_json_a_drive("manual_scraping.json", json_resultado, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Subido a Drive: [Ver archivo]({enlace})")