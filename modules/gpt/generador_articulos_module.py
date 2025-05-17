import streamlit as st
import json
import openai
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)
from modules.utils.mongo_utils import (
    obtener_documentos_mongodb,
    obtener_documento_mongodb
)

def get_openai_client():
    return openai.Client(api_key=st.secrets["openai"]["api_key"])

def obtener_rango_legible(rango):
    partes = rango.split(" - ")
    if len(partes) == 2:
        return f"entre {partes[0]} y {partes[1]} palabras"
    return rango

def generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango, tono):
    return f"""
Eres un experto en redacción SEO, copywriting y posicionamiento en Google.

A continuación tienes un resumen estructurado de las páginas mejor posicionadas en Google España (idioma {idioma.lower()}) para la palabra clave: \"{palabra_clave}\".

Este resumen se basa en la recopilación de las etiquetas HTML y contenido visible de los artículos mejor posicionados para dicha búsqueda.

Tu tarea es:
- Analizar el contenido de referencia.
- Detectar las intenciones de búsqueda del usuario.
- Identificar los temas más recurrentes y relevantes.
- Reconocer la estructura común de encabezados (H1, H2, H3).
- Estudiar el enfoque editorial de los competidores.

Luego, redacta un artículo original, más útil, más completo y mejor optimizado para SEO que los que ya existen. No repitas información innecesaria ni uses frases genéricas.

Tono sugerido: {tono}

Detalles de redacción:
Longitud: {obtener_rango_legible(rango)}
Idioma: {idioma}
Tipo de artículo: {tipo_articulo}
Formato: Utiliza subtítulos claros (H2 y H3), listas, introducción persuasiva y conclusión útil.
Objetivo: Posicionarse en Google para la keyword \"{palabra_clave}\".
No menciones que eres una IA ni expliques que estás generando un texto.
Hazlo como si fueras un redactor profesional experto en turismo y SEO.
El 30% del contenido debe ser cogido del propio JSON y parafraseado para que no se detecte como contenido duplicado.
El 85% de los párrafos deben tener más de 150 palabras.
"""

def render_generador_articulos():
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("palabra_clave", "")
    st.session_state.setdefault("prompt_extra_manual", "")

    st.title("🧠 Generador Maestro de Artículos SEO")
    st.markdown("Crea artículos SEO potentes con o sin contexto JSON. Tú tienes el control.")

    fuente = st.radio("Fuente del archivo JSON (opcional):", ["Ninguno", "Desde ordenador", "Desde Drive", "Desde MongoDB"], horizontal=True, index=0)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state["nombre_base"] = archivo.name
            st.rerun()

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return
        carpeta_id = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta_id)

        if archivos:
            elegido = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
            if st.button("📅 Cargar desde Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                st.session_state["nombre_base"] = elegido
                try:
                    crudo = st.session_state.contenido_json.decode("utf-8") if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
                    datos = json.loads(crudo)
                    st.session_state.palabra_clave = datos.get("busqueda", "")
                    st.session_state["idioma_detectado"] = datos.get("idioma", "Español")
                    st.session_state["tipo_detectado"] = datos.get("tipo_articulo", "Informativo")
                except Exception as e:
                    st.warning(f"⚠️ Error leyendo JSON: {e}")
                st.rerun()
        else:
            st.warning("⚠️ No se encontraron archivos JSON en este proyecto.")

    elif fuente == "Desde MongoDB":
        try:
            uri = "mongodb://serpy:esperanza85@serpy_mongodb:27017/?authSource=admin"
            db = "serpy"
            collection = "hoteles"
            documentos = obtener_documentos_mongodb(uri, db, collection, campo_nombre="nombre")

            if documentos:
                elegido = st.selectbox("Selecciona documento JSON desde MongoDB:", documentos)
                if st.button("📤 Cargar desde MongoDB"):
                    doc = obtener_documento_mongodb(uri, db, collection, elegido, campo_nombre="nombre")
                    if doc:
                        st.session_state.contenido_json = json.dumps(doc, ensure_ascii=False).encode("utf-8")
                        st.session_state["nombre_base"] = elegido
                        st.session_state.palabra_clave = doc.get("busqueda", "")
                        st.session_state["idioma_detectado"] = doc.get("idioma", "Español")
                        st.session_state["tipo_detectado"] = doc.get("tipo_articulo", "Informativo")
                        st.rerun()
                    else:
                        st.warning("⚠️ No se encontró el documento.")
            else:
                st.warning("⚠️ No hay documentos disponibles en MongoDB.")
        except Exception as e:
            st.error(f"❌ Error accediendo a MongoDB: {e}")

    st.markdown("---")
    tipos = ["Informativo", "Ficha de producto", "Transaccional"]
    idiomas = ["Español", "Inglés", "Francés", "Alemán"]
    rangos_palabras = ["1000 - 2000", "2000 - 3000", "3000 - 4000", "4000 - 5000"]
    modelos = ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tipo_articulo = st.selectbox("Tipo de artículo", tipos, index=0)
        recomendaciones_tono = {"Informativo": "Persuasivo", "Ficha de producto": "Persuasivo", "Transaccional": "Inspirador"}
        tono_sugerido = recomendaciones_tono.get(tipo_articulo, "Persuasivo")
        tono = st.selectbox("Tono", ["Neutro profesional", "Persuasivo", "Inspirador", "Narrativo"], index=1)
        st.session_state["tono_articulo"] = tono
    with col2:
        idioma = st.selectbox("Idioma", idiomas, index=idiomas.index(st.session_state.get("idioma_detectado", "Español")))
    with col3:
        rango = st.selectbox("Rango de palabras", rangos_palabras, index=0)
        st.session_state["rango_palabras"] = rango
    with col4:
        modelo = st.selectbox("Modelo GPT", modelos, index=0)
        st.session_state["modelo"] = modelo

    st.markdown("### Parámetros avanzados")
    st.session_state["temperature"] = st.slider("Temperature", 0.0, 1.5, 1.0, 0.1)
    st.session_state["top_p"] = st.slider("Top-p", 0.0, 1.0, 0.9, 0.05)
    st.session_state["frequency_penalty"] = st.slider("Frecuencia", 0.0, 2.0, 0.7, 0.1)
    st.session_state["presence_penalty"] = st.slider("Presencia", 0.0, 2.0, 1.0, 0.1)

    palabra_clave = st.text_input("Palabra clave principal", st.session_state.get("palabra_clave", ""))
    st.session_state["palabra_clave"] = palabra_clave

    prompt_extra = generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango, tono)
    st.text_area("Instrucciones para GPT", prompt_extra, height=300, key="autoprompt")
    st.text_area("Instrucciones adicionales", st.session_state.get("prompt_extra_manual", ""), key="prompt_extra_manual", height=150)

    if st.button("🧠 Generar artículo con GPT") and palabra_clave:
        from modules.gpt.generador_articulos_module import render_generador_articulos
        render_generador_articulos()
