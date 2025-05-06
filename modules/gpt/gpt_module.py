import streamlit as st
import json
import openai
from modules.utils.drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive

def render_gpt_module():
    st.title("🤖 Módulo GPT")
    st.markdown("### 🧠 Análisis de JSON con IA")

    openai.api_key = st.secrets["openai"]["api_key"]

    # Campo de texto para el prompt
    prompt_usuario = st.text_area(
        "✍️ Escribe un prompt para que GPT analice el JSON",
        height=150,
        placeholder="¿De qué trata este archivo JSON?"
    )

    # Selección del archivo JSON
    fuente = st.radio("Selecciona fuente del archivo JSON:", ["Desde ordenador", "Desde Drive"], horizontal=True)
    contenido_json = None

    if fuente == "Desde ordenador":
        archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
        if archivo:
            contenido_json = archivo.read().decode("utf-8")

    else:
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return

        carpeta_id = st.session_state["proyecto_id"]
        archivos_disponibles = listar_archivos_en_carpeta(carpeta_id)

        if archivos_disponibles:
            archivo_seleccionado = st.selectbox("Selecciona un archivo JSON de Drive", list(archivos_disponibles.keys()))
            if st.button("📥 Cargar desde Drive"):
                contenido_json = obtener_contenido_archivo_drive(archivos_disponibles[archivo_seleccionado])
        else:
            st.warning("⚠️ No se encontraron archivos JSON en este proyecto.")
            return

    # Si hay prompt y JSON, hacer la llamada a OpenAI
    if prompt_usuario and contenido_json:
        try:
            json_data = json.loads(contenido_json)
            contexto = f"Este es el contenido del archivo JSON:\n\n{json.dumps(json_data, ensure_ascii=False, indent=2)}"

            with st.spinner("🤖 Analizando el archivo con GPT..."):
                respuesta = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Eres un experto en análisis de contenido web estructurado en JSON."},
                        {"role": "user", "content": f"{prompt_usuario}\n\n{contexto}"}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )

                contenido_respuesta = respuesta.choices[0].message.content.strip()
                st.markdown("### 🧠 Respuesta de GPT")
                st.write(contenido_respuesta)

        except Exception as e:
            st.error(f"❌ Error al procesar el JSON o conectarse a OpenAI: {e}")
