import streamlit as st
import json
import openai
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)

def get_openai_client():
    return openai.OpenAI(api_key=st.secrets["openai"]["api_key"])

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

\U0001f5e3️ Tono sugerido: {tono}

\u270d\ufe0f Detalles de redacción:
\ud83d\udccf Longitud: {obtener_rango_legible(rango)}
\ud83c\udf0d Idioma: {idioma}
\ud83d\udcc4 Tipo de artículo: {tipo_articulo}
\ud83d\uddc2️ Formato: Utiliza subtítulos claros (H2 y H3), listas, introducción persuasiva y conclusión útil.
\ud83d\udcc8 Objetivo: Posicionarse en Google para la keyword \"{palabra_clave}\".
\ud83d\udeab No menciones que eres una IA ni expliques que estás generando un texto.
\u2705 Hazlo como si fueras un redactor profesional experto en turismo y SEO.
\ud83e\udde9 El 30% del contenido debe ser cogido del propio JSON y parafraseado para que no se detecte como contenido duplicado.
\ud83e\uddf1 El 85% de los párrafos deben tener más de 150 palabras.
"""

def estimar_coste(modelo, tokens_entrada, tokens_salida):
    precios = {
        "gpt-3.5-turbo": (0.0005, 0.0015),
        "gpt-4o-mini": (0.0005, 0.0015),
        "gpt-4.1-nano": (0.0010, 0.0030),
        "gpt-4.1-mini": (0.0015, 0.0045),
        "gpt-4o": (0.0050, 0.0150),
        "gpt-4-turbo": (0.0100, 0.0300)
    }
    entrada_usd, salida_usd = precios.get(modelo, (0, 0))
    return tokens_entrada / 1000 * entrada_usd, tokens_salida / 1000 * salida_usd

def render_generador_articulos():
    st.session_state["_called_script"] = "generador_articulos"
    st.title("\U0001f9e0 Generador Maestro de Artículos SEO")
    st.markdown("Crea artículos SEO potentes con o sin contexto JSON. Tú tienes el control.")

    client = get_openai_client()

    st.session_state.setdefault("maestro_articulo", None)
    st.session_state.setdefault("palabra_clave", "")
    st.session_state.setdefault("contenido_json", None)
    st.session_state.setdefault("idioma_detectado", None)
    st.session_state.setdefault("tipo_detectado", None)
    st.session_state.setdefault("mensaje_busqueda", "")
    st.session_state.setdefault("prompt_extra_manual", "")

    fuente = st.radio("\ud83d\udcc2 Fuente del archivo JSON (opcional):", ["Ninguno", "Desde ordenador", "Desde Drive"], horizontal=True, index=2)

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("\ud83d\udcc1 Sube un archivo JSON", type="json")
        if archivo:
            st.session_state.contenido_json = archivo.read()
            st.session_state["nombre_base"] = archivo.name
            st.session_state.palabra_clave_fijada = False
            st.session_state.mensaje_busqueda = ""
            st.rerun()

    elif fuente == "Desde Drive":
        if "proyecto_id" not in st.session_state:
            st.error("\u274c Selecciona primero un proyecto en la barra lateral.")
            return
        carpeta_id = obtener_o_crear_subcarpeta("scraper etiquetas google", st.session_state.proyecto_id)
        archivos = listar_archivos_en_carpeta(carpeta_id)

        if archivos:
            elegido = st.selectbox("Selecciona archivo JSON:", list(archivos.keys()))
            if st.button("\ud83d\uddd5\ufe0f Cargar desde Drive"):
                st.session_state.contenido_json = obtener_contenido_archivo_drive(archivos[elegido])
                st.session_state["nombre_base"] = elegido
                st.session_state.palabra_clave_fijada = False
                try:
                    crudo = st.session_state.contenido_json.decode("utf-8") if isinstance(st.session_state.contenido_json, bytes) else st.session_state.contenido_json
                    datos = json.loads(crudo)
                    st.session_state.palabra_clave = datos.get("busqueda", "")
                    st.session_state.idioma_detectado = datos.get("idioma", None)
                    st.session_state.tipo_detectado = datos.get("tipo_articulo", None)
                except Exception as e:
                    st.session_state.mensaje_busqueda = f"Error leyendo JSON: {e}"
                st.rerun()
        else:
            st.warning("\u26a0\ufe0f No se encontraron archivos JSON en este proyecto.")

    # A partir de aquí continúa con los parámetros, inputs y generación del artículo como en tu código base,
    # utilizando `client.chat.completions.create(...)` cuando llegue el momento de la generación.
    # El resto de la lógica no requiere cambios mayores para adaptarse a la nueva versión.

    # Si quieres, puedo completar también esa parte final con las descargas, render y subida a Drive.
