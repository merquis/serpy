import streamlit as st
import json
import openai
from modules.utils.drive_utils import listar_archivos_en_carpeta, obtener_contenido_archivo_drive, subir_archivo_a_drive

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
    modelo = "gpt-3.5-turbo"  # valor por defecto

    if fuente == "Desde ordenador":
        col1, col2 = st.columns([3, 1])
        with col1:
            archivo = st.file_uploader("📁 Sube un archivo JSON", type="json")
            if archivo:
                contenido_json = archivo.read().decode("utf-8")
        with col2:
            modelo = st.selectbox("Modelo", ["gpt-3.5-turbo", "gpt-4"], index=0)

    else:
        if "proyecto_id" not in st.session_state:
            st.error("❌ Selecciona primero un proyecto en la barra lateral.")
            return

        carpeta_id = st.session_state["proyecto_id"]
        archivos_disponibles = listar_archivos_en_carpeta(carpeta_id)

        if archivos_disponibles:
            col1, col2 = st.columns([3, 1])
            with col1:
                archivo_seleccionado = st.selectbox("Selecciona un archivo JSON de Drive", list(archivos_disponibles.keys()))
            with col2:
                modelo = st.selectbox("Modelo", ["gpt-3.5-turbo", "gpt-4"], index=0)

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
                    model=modelo,
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

                # Descargar como JSON
                st.download_button(
                    label="💾 Descargar respuesta como JSON",
                    file_name="respuesta_gpt.json",
                    mime="application/json",
                    data=json.dumps({
                        "modelo": modelo,
                        "prompt": prompt_usuario,
                        "respuesta": contenido_respuesta
                    }, ensure_ascii=False, indent=2)
                )

                # Subir a Google Drive
                if "proyecto_id" in st.session_state:
                    if st.button("☁️ Subir respuesta a Google Drive"):
                        subir_archivo_a_drive(
                            contenido=json.dumps({
                                "modelo": modelo,
                                "prompt": prompt_usuario,
                                "respuesta": contenido_respuesta
                            }, ensure_ascii=False, indent=2),
                            nombre_archivo="respuesta_gpt.json",
                            carpeta_id=st.session_state["proyecto_id"]
                        )
                        st.success("✅ Respuesta subida a Google Drive correctamente.")

        except Exception as e:
            st.error(f"❌ Error al procesar el JSON o conectarse a OpenAI: {e}")
