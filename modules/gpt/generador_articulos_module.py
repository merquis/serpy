import streamlit as st
import openai
import json
from modules.utils.drive_utils import subir_json_a_drive

def render_generador_articulos():
    st.title("📝 Generador de artículos con GPT")
    st.markdown("Genera artículos automáticamente a partir de una palabra clave, eligiendo tipo e idioma.")

    openai.api_key = st.secrets["openai"]["api_key"]

    # Estado inicial
    if "articulo_generado" not in st.session_state:
        st.session_state.articulo_generado = None

    col1, col2 = st.columns(2)
    with col1:
        tipo_articulo = st.selectbox("📄 Tipo de artículo", [
            "Informativo",
            "Ficha de producto",
            "Transaccional"
        ])
        idioma = st.selectbox("🌍 Idioma", ["Español", "Inglés", "Francés", "Alemán"])
    with col2:
        modelo = st.selectbox("🤖 Modelo", ["gpt-3.5-turbo", "gpt-4"], index=0)

    palabra_clave = st.text_input("🔑 Palabra clave o tema del artículo")

    if st.button("✍️ Generar artículo con GPT") and palabra_clave.strip():
        prompt = construir_prompt(tipo_articulo, idioma, palabra_clave)
        with st.spinner("🧠 Generando artículo..."):
            try:
                response = openai.ChatCompletion.create(
                    model=modelo,
                    messages=[
                        {"role": "system", "content": "Eres un redactor profesional SEO y copywriter."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1500
                )
                contenido = response.choices[0].message.content.strip()
                st.session_state.articulo_generado = {
                    "tipo": tipo_articulo,
                    "idioma": idioma,
                    "modelo": modelo,
                    "tema": palabra_clave,
                    "contenido": contenido
                }
            except Exception as e:
                st.error(f"❌ Error al generar el artículo: {e}")

    if st.session_state.articulo_generado:
        st.markdown("### 📰 Artículo generado")
        st.write(st.session_state.articulo_generado["contenido"])

        resultado_json = json.dumps(st.session_state.articulo_generado, ensure_ascii=False, indent=2).encode("utf-8")

        st.download_button(
            label="💾 Descargar como JSON",
            file_name="articulo_generado.json",
            mime="application/json",
            data=resultado_json
        )

        if "proyecto_id" in st.session_state:
            if st.button("☁️ Subir a Google Drive"):
                nombre_archivo = f"Articulo_{palabra_clave.replace(' ', '_')}.json"
                enlace = subir_json_a_drive(nombre_archivo, resultado_json, st.session_state["proyecto_id"])
                if enlace:
                    st.success(f"✅ Archivo subido: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir el archivo a Drive.")


def construir_prompt(tipo, idioma, keyword):
    return f"""
Quiero que redactes un artículo de tipo "{tipo}" en idioma "{idioma.lower()}". 
El tema central debe ser: "{keyword}".

Hazlo con un estilo claro, persuasivo y enfocado al SEO.
Incluye subtítulos y estructura útil para lectores reales.
No menciones que eres un modelo de lenguaje ni hagas introducciones impersonales.
"""
