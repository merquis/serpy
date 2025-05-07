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
📏 Longitud: {obtener_rango_legible(rango)}
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
    st.session_state.setdefault("prompt_extra_manual", "")

    # ... [todo el código de selección de fuente, parámetros, etc. sin cambios] ...

    st.markdown("### 🎛️ Parámetros avanzados del modelo")

    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider(
            "🔥 Temperature (creatividad)", 0.0, 1.5, 0.9, 0.1,
            help="Controla la creatividad. Más alto = más original pero menos consistente."
        )
        top_p = st.slider(
            "📊 Top-p (variedad del muestreo)", 0.0, 1.0, 1.0, 0.05,
            help="Controla qué tan amplio es el rango de palabras posibles."
        )
    with col2:
        frequency_penalty = st.slider(
            "🔁 Penalización por frecuencia (evita repeticiones)", 0.0, 2.0, 0.4, 0.1,
            help="Reduce la repetición de las mismas frases o expresiones."
        )
        presence_penalty = st.slider(
            "🆕 Penalización por presencia (fomenta ideas nuevas)", 0.0, 2.0, 0.6, 0.1,
            help="Incentiva que el modelo introduzca temas no mencionados aún."
        )

    # ... [el resto del código continúa igual, usando esas variables en la llamada a OpenAI] ...

    resp = openai.ChatCompletion.create(
        model=modelo,
        messages=[
            {"role": "system", "content": "Eres un redactor profesional experto en SEO."},
            {"role": "user", "content": prompt_final.strip()}
        ],
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        max_tokens=tokens_salida
    )
