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
    st.session_state.setdefault("prompt_extra_manual", "")
    st.session_state.setdefault("palabra_clave", "")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tipo_articulo = st.selectbox("📄 Tipo de artículo", ["Informativo", "Ficha de producto", "Transaccional"])
    with col2:
        tono = st.selectbox("🎙️ Tono del artículo", ["Neutro profesional", "Persuasivo", "Informal", "Inspirador", "Narrativo"],
                             index=["Neutro profesional", "Persuasivo", "Informal", "Inspirador", "Narrativo"].index(st.session_state["tono_articulo"]))
        st.session_state["tono_articulo"] = tono
    with col3:
        presence_penalty = st.slider("🔁 Evitar repeticiones", min_value=0.0, max_value=2.0, step=0.1,
                                     value=st.session_state["presence_penalty"])
        st.session_state["presence_penalty"] = presence_penalty
    with col4:
        modelo = st.selectbox("🤖 Modelo GPT", ["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4o", "gpt-4-turbo"])

    palabra_clave = st.text_input("🔑 Palabra clave principal", value=st.session_state["palabra_clave"])
    st.session_state["palabra_clave"] = palabra_clave

    rango_palabras = "3000 - 4000"
    idioma = "Español"

    prompt_extra = generar_prompt_extra(palabra_clave, idioma, tipo_articulo, rango_palabras)
    st.text_area("🧠 Prompt generado", value=prompt_extra, height=300)

    prompt_manual = st.text_area("✍️ Instrucciones adicionales personalizadas",
                                 value=st.session_state.get("prompt_extra_manual", ""),
                                 height=150)

    st.session_state["prompt_extra_manual"] = prompt_manual

    if st.button("🚀 Generar artículo"):
        prompt_completo = prompt_extra + "\n" + prompt_manual

        with st.spinner("Generando artículo con GPT..."):
            try:
                respuesta = openai.ChatCompletion.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un redactor profesional experto en SEO."},
                        {"role": "user", "content": prompt_completo.strip()}
                    ],
                    temperature=0.9,
                    top_p=1.0,
                    frequency_penalty=0.4,
                    presence_penalty=presence_penalty,
                    max_tokens=2800
                )

                contenido_generado = respuesta.choices[0].message.content.strip()
                st.session_state["maestro_articulo"] = contenido_generado

                st.success("✅ Artículo generado con éxito")
                st.markdown("### 📰 Artículo generado")
                st.write(contenido_generado)

                json_resultado = json.dumps({
                    "tipo": tipo_articulo,
                    "tono": tono,
                    "modelo": modelo,
                    "keyword": palabra_clave,
                    "contenido": contenido_generado
                }, ensure_ascii=False, indent=2).encode("utf-8")

                st.download_button("⬇️ Descargar JSON", data=json_resultado,
                                   file_name="articulo_generado.json",
                                   mime="application/json")

                if st.button("☁️ Subir a Google Drive"):
                    if "proyecto_id" not in st.session_state:
                        st.error("❌ No se ha seleccionado un proyecto.")
                        return

                    subcarpeta = obtener_o_crear_subcarpeta("posts automaticos", st.session_state["proyecto_id"])
                    enlace = subir_json_a_drive("articulo_generado.json", json_resultado, subcarpeta)
                    if enlace:
                        st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                    else:
                        st.error("❌ Error al subir archivo a Drive.")

            except Exception as e:
                st.error(f"❌ Error al generar el artículo: {str(e)}")
