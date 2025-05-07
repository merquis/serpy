import streamlit as st
import openai
import json
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive
)

def render_generador_articulos():
    st.title("🧠 Generador Maestro de Artículos SEO")
    st.markdown("Crea artículos SEO potentes con o sin contexto JSON. Tú tienes el control.")

    openai.api_key = st.secrets["openai"]["api_key"]

    if "maestro_articulo" not in st.session_state:
        st.session_state.maestro_articulo = None

    if "palabra_clave" not in st.session_state:
        st.session_state.palabra_clave = ""

    if "contenido_json" not in st.session_state:
        st.session_state.contenido_json = None

    contenido_json = None
    nombre_archivo_json = ""

    # ░░░ CARGA DE JSON (opcional)
    fuente = st.radio("📂 Fuente del archivo JSON (opcional):", ["Ninguno", "Desde ordenador", "Desde Drive"], horizontal=True)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            contenido_json = archivo.read().decode("utf-8")
            st.session_state.contenido_json = contenido_json
            nombre_archivo_json = archivo.name
            try:
                datos = json.loads(contenido_json)
                st.session_state.palabra_clave = datos.get("busqueda", "")
            except Exception as e:
                st.warning("⚠️ Error al leer JSON: " + str(e))

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return

        carpeta_id = st.session_state["proyecto_id"]
        archivos_disponibles = listar_archivos_en_carpeta(carpeta_id)

        if archivos_disponibles:
            archivo_seleccionado = st.selectbox("Selecciona archivo JSON:", list(archivos_disponibles.keys()))
            if st.button("📥 Cargar desde Drive"):
                contenido_json = obtener_contenido_archivo_drive(archivos_disponibles[archivo_seleccionado])
                st.session_state.contenido_json = contenido_json
                st.session_state["nombre_base"] = archivo_seleccionado
                try:
                    datos = json.loads(contenido_json)
                    st.session_state.palabra_clave = datos.get("busqueda", "")
                except Exception as e:
                    st.warning("⚠️ Error al leer JSON: " + str(e))
                st.experimental_rerun()
        else:
            st.warning("⚠️ No se encontraron archivos JSON en este proyecto.")

    # ░░░ PARÁMETROS DE GENERACIÓN
    st.markdown("---")
    st.subheader("⚙️ Parámetros del artículo")

    col1, col2 = st.columns(2)
    with col1:
        tipo_articulo = st.selectbox("📄 Tipo de artículo", ["Informativo", "Ficha de producto", "Transaccional"])
        idioma = st.selectbox("🌍 Idioma", ["Español", "Inglés", "Francés", "Alemán"])
    with col2:
        modelo = st.selectbox("🤖 Modelo GPT", ["gpt-3.5-turbo", "gpt-4"], index=0)

    palabra_clave = st.text_area("🔑 Palabra clave principal", value=st.session_state.palabra_clave, height=80, key="palabra_clave_input")
    st.session_state.palabra_clave = palabra_clave

    prompt_extra = st.text_area("💬 Prompt adicional (opcional)", placeholder="Puedes dar instrucciones extra, tono, estructura, etc.", height=120)

    if st.button("✍️ Generar artículo con GPT") and palabra_clave.strip():
        contexto = ""
        contenido_json = st.session_state.get("contenido_json", None)
        if contenido_json:
            try:
                datos = json.loads(contenido_json)
                contexto = f"\n\nEste es el contenido estructurado de referencia:\n{json.dumps(datos, ensure_ascii=False, indent=2)}"
            except Exception as e:
                st.warning("⚠️ No se pudo usar el JSON como contexto.")

        prompt_final = f"""
Quiero que redactes un artículo de tipo \"{tipo_articulo}\" en idioma \"{idioma.lower()}\".
La palabra clave principal es: \"{palabra_clave}\".

{prompt_extra.strip() if prompt_extra else ""}

{contexto}

Hazlo con estilo profesional, orientado al SEO, con subtítulos útiles, sin mencionar que eres un modelo.
"""

        with st.spinner("🧠 Generando artículo..."):
            try:
                response = openai.ChatCompletion.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un redactor profesional experto en SEO."},
                        {"role": "user", "content": prompt_final.strip()}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                contenido = response.choices[0].message.content.strip()
                st.session_state.maestro_articulo = {
                    "tipo": tipo_articulo,
                    "idioma": idioma,
                    "modelo": modelo,
                    "keyword": palabra_clave,
                    "prompt_extra": prompt_extra,
                    "contenido": contenido,
                    "json_usado": st.session_state.get("nombre_base", None)
                }
            except Exception as e:
                st.error(f"❌ Error al generar el artículo: {e}")

    if st.session_state.maestro_articulo:
        st.markdown("### 📰 Artículo generado")
        st.write(st.session_state.maestro_articulo["contenido"])

        resultado_json = json.dumps(st.session_state.maestro_articulo, ensure_ascii=False, indent=2).encode("utf-8")

        st.download_button(
            label="💾 Descargar como JSON",
            file_name="articulo_maestro.json",
            mime="application/json",
            data=resultado_json
        )

        if "proyecto_id" in st.session_state:
            if st.button("☁️ Subir a Google Drive"):
                nombre_archivo = f"ArticuloGPT_{palabra_clave.replace(' ', '_')}.json"
                enlace = subir_json_a_drive(nombre_archivo, resultado_json, st.session_state["proyecto_id"])
                if enlace:
                    st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir el archivo a Drive.")
