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

    # ── Estado inicial ───────────────────────────────────────────────
    st.session_state.setdefault("maestro_articulo", None)
    st.session_state.setdefault("palabra_clave", "")
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("idioma_detectado", None)
    st.session_state.setdefault("tipo_detectado", None)
    st.session_state.setdefault("mensaje_busqueda", "")   # ← mensaje persistente

    # ── Mostrar mensaje si existe (permanece tras rerun) ─────────────
    if st.session_state.mensaje_busqueda:
        st.markdown(f"🔍 **Palabra clave detectada**: `{st.session_state.mensaje_busqueda}`")

    # ── Procesar JSON ya cargado (una sola vez) ──────────────────────
    if ("nombre_base" in st.session_state
        and st.session_state.contenido_json
        and not st.session_state.get("palabra_clave_fijada", False)):
        try:
            crudo = (st.session_state.contenido_json
                     .decode("utf-8") if isinstance(st.session_state.contenido_json, bytes)
                     else st.session_state.contenido_json)
            datos = json.loads(crudo)
            st.session_state.palabra_clave    = datos.get("busqueda", "")
            st.session_state.idioma_detectado = datos.get("idioma", None)
            st.session_state.tipo_detectado   = datos.get("tipo_articulo", None)
            st.session_state.palabra_clave_fijada = True
        except Exception as e:
            st.warning(f"⚠️ Error al analizar JSON: {e}")

    # ── Carga de JSON ────────────────────────────────────────────────
    fuente = st.radio("📂 Fuente del archivo JSON (opcional):",
                      ["Ninguno", "Desde ordenador", "Desde Drive"],
                      horizontal=True)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state["nombre_base"] = archivo.name
            st.session_state.palabra_clave_fijada = False
            st.experimental_rerun()

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return
        carpeta_id = st.session_state.proyecto_id
        archivos = listar_archivos_en_carpeta(carpeta_id)

        if archivos:
            elegido = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
            if st.button("📥 Cargar desde Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                st.session_state["nombre_base"] = elegido
                st.session_state.palabra_clave_fijada = False

                # Guardar mensaje y hacer rerun
                try:
                    crudo = (st.session_state.contenido_json
                             .decode("utf-8") if isinstance(st.session_state.contenido_json, bytes)
                             else st.session_state.contenido_json)
                    datos = json.loads(crudo)
                    st.session_state.mensaje_busqueda = datos.get("busqueda", "No encontrada")
                except Exception as e:
                    st.session_state.mensaje_busqueda = f"Error: {e}"
                st.experimental_rerun()
        else:
            st.warning("⚠️ No se encontraron archivos JSON en este proyecto.")

    # ── Parámetros del artículo ──────────────────────────────────────
    st.markdown("---")
    st.subheader("⚙️ Parámetros del artículo")

    tipos   = ["Informativo", "Ficha de producto", "Transaccional"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]

    col1, col2 = st.columns(2)
    with col1:
        tipo_articulo = st.selectbox(
            "📄 Tipo de artículo", tipos,
            index=tipos.index(st.session_state.tipo_detectado)
                  if st.session_state.tipo_detectado in tipos else 0
        )
        idioma = st.selectbox(
            "🌍 Idioma", idiomas,
            index=idiomas.index(st.session_state.idioma_detectado)
                  if st.session_state.idioma_detectado in idiomas else 0
        )
    with col2:
        modelo = st.selectbox("🤖 Modelo GPT", ["gpt-3.5-turbo", "gpt-4"], index=0)

    # ── Palabra clave principal ──────────────────────────────────────
    st.session_state.setdefault("palabra_clave_input", st.session_state.palabra_clave)
    palabra_clave = st.text_area("🔑 Palabra clave principal",
                                 value=st.session_state.palabra_clave_input,
                                 height=80,
                                 key="palabra_clave_input")
    st.session_state.palabra_clave = palabra_clave

    # ── Prompt adicional ────────────────────────────────────────────
    prompt_extra = st.text_area(
        "💬 Prompt adicional (opcional)",
        placeholder="Puedes dar instrucciones extra, tono, estructura, etc.",
        height=120
    )

    # ── Generar artículo ────────────────────────────────────────────
    if st.button("✍️ Generar artículo con GPT") and palabra_clave.strip():
        contexto = ""
        if st.session_state.contenido_json:
            try:
                crudo = (st.session_state.contenido_json
                         .decode("utf-8") if isinstance(st.session_state.contenido_json, bytes)
                         else st.session_state.contenido_json)
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

    # ── Resultado y exportación ─────────────────────────────────────
    if st.session_state.maestro_articulo:
        st.markdown("### 📰 Artículo generado")
        st.write(st.session_state.maestro_articulo["contenido"])

        resultado_json = json.dumps(
            st.session_state.maestro_articulo,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")

        st.download_button("💾 Descargar como JSON",
                           data=resultado_json,
                           file_name="articulo_maestro.json",
                           mime="application/json")

        if "proyecto_id" in st.session_state:
            if st.button("☁️ Subir a Google Drive"):
                enlace = subir_json_a_drive(
                    f"ArticuloGPT_{palabra_clave.replace(' ', '_')}.json",
                    resultado_json,
                    st.session_state.proyecto_id
                )
                if enlace:
                    st.success(f"✅ Subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir el archivo a Drive.")
