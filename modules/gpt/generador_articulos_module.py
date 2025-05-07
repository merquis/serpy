import streamlit as st
import openai
import json
from modules.utils.drive_utils import (
    listar_archivos_en_carpeta,
    obtener_contenido_archivo_drive,
    subir_json_a_drive,
    obtener_o_crear_subcarpeta
)

def obtener_rango_legible(rango):
    partes = rango.split(" - ")
    if len(partes) == 2:
        return f"entre {partes[0]} y {partes[1]} palabras"
    return rango

def generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango):
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

✍️ Detalles de redacción:
🔢 Longitud: {obtener_rango_legible(rango)}
🌍 Idioma: {idioma}
📄 Tipo de artículo: {tipo_articulo}
🗂️ Formato: Utiliza subtítulos claros (H2 y H3), listas, introducción persuasiva y conclusión útil.
📈 Objetivo: Posicionarse en Google para la keyword \"{palabra_clave}\".
🚫 No menciones que eres una IA ni expliques que estás generando un texto.
✅ Hazlo como si fueras un redactor profesional experto en turismo y SEO.
🧩 El 30% del contenido debe ser cogido del propio JSON y parafraseado para que no se detecte como contenido duplicado.
🧱 El 85% de los párrafos deben tener más de 150 palabras.
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
    st.session_state.setdefault("presence_penalty", 0.4)
    st.session_state.setdefault("tono_articulo", "Neutro profesional")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tipo_articulo = st.selectbox("📄 Tipo de artículo", ["Informativo", "Ficha de producto", "Transaccional"])
    with col2:
        tono = st.selectbox("🎙️ Tono del artículo", ["Neutro profesional", "Persuasivo", "Informal", "Inspirador", "Narrativo"],
                             index=0 if st.session_state["tono_articulo"] not in ["Persuasivo", "Informal", "Inspirador", "Narrativo"] else ["Persuasivo", "Informal", "Inspirador", "Narrativo"].index(st.session_state["tono_articulo"]) + 1)
        st.session_state["tono_articulo"] = tono
    with col3:
        presence_penalty = st.slider("🔁 Evitar repeticiones", min_value=0.0, max_value=2.0, step=0.1,
                                     value=st.session_state["presence_penalty"])
        st.session_state["presence_penalty"] = presence_penalty
    with col4:
        modelo = st.selectbox("🤖 Modelo GPT", ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"])

    st.write("\n⚙️ Parámetros configurados correctamente. Listo para continuar con la generación del artículo.")
