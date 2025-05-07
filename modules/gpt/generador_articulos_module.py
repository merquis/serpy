import streamlit as st
import openai
import json
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)

def render_generador_articulos():
    st.session_state["_called_script"] = "generador_articulos"
    st.title("🧠 Generador Maestro de Artículos SEO")
    st.markdown("Crea artículos SEO potentes con o sin contexto JSON. Tú tienes el control.")

    openai.api_key = st.secrets["openai"]["api_key"]

    st.session_state.setdefault("maestro_articulo", None)
    st.session_state.setdefault("palabra_clave", "")
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("idioma_detectado", None)
    st.session_state.setdefault("tipo_detectado", None)
    st.session_state.setdefault("mensaje_busqueda", "")

    # Fuente del JSON
    fuente = st.radio("📂 Fuente del archivo JSON (opcional):",
                      ["Ninguno", "Desde ordenador", "Desde Drive"],
                      horizontal=True, index=0)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state["nombre_base"] = archivo.name
            st.session_state.palabra_clave_fijada = False
            st.session_state.mensaje_busqueda = ""
            st.experimental_rerun()

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return

        carpeta_principal = st.session_state.proyecto_id
        subcarpeta_etiquetas = obtener_o_crear_subcarpeta("scraper etiquetas google", carpeta_principal)
        archivos = listar_archivos_en_carpeta(subcarpeta_etiquetas)

        if archivos:
            elegido = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
            if st.button("📥 Cargar desde Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                st.session_state["nombre_base"] = elegido
                st.session_state.palabra_clave_fijada = False

                try:
                    crudo = st.session_state.contenido_json.decode("utf-8") \
                        if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
                    datos = json.loads(crudo)
                    st.session_state.mensaje_busqueda = datos.get("busqueda", "No encontrada")
                except Exception as e:
                    st.session_state.mensaje_busqueda = f"Error leyendo JSON: {e}"

                st.experimental_rerun()
        else:
            st.warning("⚠️ No se encontraron archivos JSON en esta subcarpeta del proyecto.")

    if st.session_state.mensaje_busqueda:
        st.markdown(f"🔍 **Palabra clave detectada**: `{st.session_state.mensaje_busqueda}`")

    if (
        "nombre_base" in st.session_state and
        st.session_state.contenido_json and
        not st.session_state.get("palabra_clave_fijada", False)
    ):
        try:
            crudo = st.session_state.contenido_json.decode("utf-8") \
                if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
            datos = json.loads(crudo)
            st.session_state.palabra_clave = datos.get("busqueda", "")
            st.session_state.idioma_detectado = datos.get("idioma", None)
            st.session_state.tipo_detectado = datos.get("tipo_articulo", None)
            st.session_state["palabra_clave_fijada"] = True
        except Exception as e:
            st.warning(f"⚠️ Error al analizar JSON: {e}")

    st.markdown("---")
    st.subheader("⚙️ Parámetros del artículo")

    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]

    col1, col2 = st.columns(2)
    with col1:
        tipo_articulo = st.selectbox("📄 Tipo de artículo", tipos,
            index=tipos.index(st.session_state.tipo_detectado) if st.session_state.tipo_detectado in tipos else 0)
        idioma = st.selectbox("🌍 Idioma", idiomas,
            index=idiomas.index(st.session_state.idioma_detectado) if st.session_state.idioma_detectado in idiomas else 0)
    with col2:
        modelo = st.selectbox("🤖 Modelo GPT", ["gpt-3.5-turbo", "gpt-4"], index=0)

    st.session_state.setdefault("palabra_clave_input", st.session_state.palabra_clave)
    palabra_clave = st.text_area("🔑 Palabra clave principal", value=st.session_state.palabra_clave_input,
                                 height=80, key="palabra_clave_input")
    st.session_state.palabra_clave = palabra_clave

    prompt_extra = st.text_area("💬 Prompt adicional (opcional)",
                                placeholder="Puedes dar instrucciones extra, tono, estructura, etc.",
                                height=120)

    if st.button("✍️ Generar artículo con GPT") and palabra_clave.strip():
        contexto = ""
        if st.session_state.contenido_json:
            try:
                crudo = st.session_state.contenido_json.decode("utf-8") \
                    if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
                datos = json.loads(crudo)
                contexto = "\n\nEste es el contenido estructurado de referencia:\n" + \
                           json.dumps(datos, ensure_ascii=False, indent=2)
            except Exception as e:
                st.warning(f"⚠️ No se pudo usar el JSON: {e}")

        prompt_final = f"""
Quiero que redactes un artículo de tipo "{tipo_articulo}" en idioma "{idioma.lower()}".
La palabra clave principal es: "{palabra_clave}".

{prompt_extra.strip() if prompt_extra else ""}

{contexto}

Hazlo con estilo profesional, orientado al SEO, con subtítulos útiles,
sin mencionar que eres un modelo.
"""

        with st.spinner("🧠 Generando artículo..."):
            try:
                resp = openai.ChatCompletion.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un redactor profesional experto en SEO."},
                        {"role": "user",    "content": prompt_final.strip()}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                st.session_state.maestro_articulo = {
                    "tipo": tipo_articulo,
                    "idioma": idioma,
                    "modelo": modelo,
                    "keyword": palabra_clave,
                    "prompt_extra": prompt_extra,
                    "contenido": resp.choices[0].message.content.strip(),
                    "json_usado": st.session_state.get("nombre_base")
                }
            except Exception as e:
                st.error(f"❌ Error al generar el artículo: {e}")

    if st.session_state.maestro_articulo:
        st.markdown("### 📰 Artículo generado")
        st.write(st.session_state.maestro_articulo["contenido"])

        resultado_json = json.dumps(st.session_state.maestro_articulo, ensure_ascii=False, indent=2).encode("utf-8")

        default_name = st.session_state.maestro_articulo["keyword"].strip().lower().replace(" ", "_") + "_post.json"
        if fuente == "Ninguno":
            nombre_archivo = st.text_input("📄 Nombre del archivo a exportar", value=default_name, key="nombre_archivo_json")
        else:
            nombre_archivo = default_name

        col = st.columns([1, 1])
        with col[0]:
            st.download_button("⬇️ Exportar JSON", data=resultado_json, file_name=nombre_archivo, mime="application/json")
        with col[1]:
            if st.button("☁️ Subir archivo a Google Drive", key="subir_drive_gpt"):
                if "proyecto_id" not in st.session_state:
                    st.error("❌ No se ha seleccionado un proyecto.")
                else:
                    subcarpeta = obtener_o_crear_subcarpeta("posts automaticos", st.session_state["proyecto_id"])
                    if not subcarpeta:
                        st.error("❌ No se pudo acceder a la subcarpeta 'posts automaticos'.")
                        return
                    enlace = subir_json_a_drive(nombre_archivo, resultado_json, subcarpeta)
                    if enlace:
                        st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                    else:
                        st.error("❌ Error al subir archivo a Drive.")
