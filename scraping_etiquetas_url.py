import json
import streamlit as st
from drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive
from bs4 import BeautifulSoup
import requests

# Interfaz para extraer etiquetas desde JSON o Drive

def render_scraping_etiquetas_url():
    st.title("🧬 Extraer etiquetas de URLs desde archivo JSON o Drive")
    st.markdown("### 📁 Origen del archivo de URLs")

    fuente = st.radio("Selecciona fuente del archivo:", ["Desde ordenador", "Desde Drive"], horizontal=True)

    def procesar_json(crudo):
        try:
            if isinstance(crudo, bytes): crudo = crudo.decode("utf-8")
            return json.loads(crudo)
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {e}")
            return None

    if fuente == "Desde ordenador":
        archivo_subido = st.file_uploader("Sube archivo JSON", type="json")
        if archivo_subido:
            st.session_state.json_contenido = archivo_subido.read()
            st.session_state.json_nombre = archivo_subido.name
    else:
        if not st.session_state.proyecto_id:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return
        archivos = listar_archivos_en_carpeta(st.session_state.proyecto_id)
        if archivos:
            seleccionado = st.selectbox("Selecciona un archivo de Drive", list(archivos.keys()))
            if st.button("📥 Cargar archivo de Drive"):
                st.session_state.json_contenido = obtener_contenido_archivo_drive(archivos[seleccionado])
                st.session_state.json_nombre = seleccionado
        else:
            st.warning("⚠️ No hay archivos JSON en este proyecto.")
            return

    if 'json_contenido' in st.session_state:
        st.success(f"✅ Archivo cargado: {st.session_state.json_nombre}")
        datos = procesar_json(st.session_state.json_contenido)
        if not datos: return

        urls = []
        for e in datos:
            if isinstance(e.get('urls'), list):
                urls += e['urls']
            elif isinstance(e.get('urls'), dict):
                urls.append(e['urls'].get('url'))

        if not urls:
            st.warning("⚠️ No se encontraron URLs en el archivo.")
            return

        st.markdown("### 🏷️ Etiquetas a extraer")
        opciones = {"title": st.checkbox("title"), "description": st.checkbox("description"),
                    "h1": st.checkbox("H1"), "h2": st.checkbox("H2"), "h3": st.checkbox("H3")}
        etiquetas = [k for k, v in opciones.items() if v]
        if not etiquetas:
            st.info("ℹ️ Selecciona al menos una etiqueta.")
            return
        if st.button("🔎 Extraer etiquetas"):
            resultados = []
            for u in urls:
                try:
                    r = requests.get(u, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                    soup = BeautifulSoup(r.text, "html.parser")
                    info = {"url": u}
                    if "title" in etiquetas:
                        info["title"] = soup.title.string.strip() if soup.title else None
                    if "description" in etiquetas:
                        desc = soup.find("meta", attrs={"name":"description"})
                        info["description"] = desc["content"].strip() if desc else None
                    for tag in ["h1","h2","h3"]:
                        if tag in etiquetas:
                            info[tag] = [t.get_text(strip=True) for t in soup.find_all(tag)]
                    resultados.append(info)
                except Exception as e:
                    resultados.append({"url": u, "error": str(e)})
            st.subheader("📦 Resultados obtenidos")
            st.json(resultados)
            st.download_button("⬇️ Descargar JSON", data=json.dumps(resultados, ensure_ascii=False, indent=2).encode("utf-8"), file_name="etiquetas.json", mime="application/json")
