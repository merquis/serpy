import streamlit as st
import openai
import json
from modules.utils.drive_utils import subir_json_a_drive

def render_chat_libre():
    st.title("\U0001F4AC Chat libre con GPT")
    st.markdown("Conversación sin restricciones, con historial, guardado y subida a Drive.")

    openai.api_key = st.secrets["openai"]["api_key"]

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "proyecto_id" not in st.session_state:
        st.warning("⚠️ No hay proyecto activo. Selecciona uno en la barra lateral para poder subir a Drive.")

    modelos = [
        "gpt-4o",         # más barato
        "gpt-3.5-turbo",
        "gpt-4-turbo"     # más caro
    ]
    modelo = st.selectbox("🤖 Elige el modelo (estimado 50k tokens + 3500 palabras)", modelos, index=0)

    def enviar_mensaje():
        mensaje = st.session_state.get("user_input", "").strip()
        if mensaje:
            st.session_state.chat_history.append({"role": "user", "content": mensaje})
            st.session_state.user_input = ""

            with st.spinner("GPT está escribiendo..."):
                try:
                    respuesta = openai.ChatCompletion.create(
                        model=modelo,
                        messages=st.session_state.chat_history,
                        temperature=0.7,
                        max_tokens=1500
                    )
                    mensaje_gpt = respuesta.choices[0].message.content.strip()
                    st.session_state.chat_history.append({"role": "assistant", "content": mensaje_gpt})
                except Exception as e:
                    st.error(f"❌ Error al contactar con OpenAI: {e}")

    # Mostrar historial
    st.markdown("### 📝 Historial de conversación")
    for mensaje in st.session_state.chat_history:
        if mensaje["role"] == "user":
            st.markdown(f"**🧑 Tú:** {mensaje['content']}")
        else:
            st.markdown(f"**🤖 GPT:** {mensaje['content']}")

    st.markdown("---")
    with st.container():
        # Campo de texto al final de la página
        st.markdown("""
        <style>
            div[data-testid="stVerticalBlock"] div:has(> .element-container textarea) {
                position: fixed;
                bottom: 90px;
                left: 0;
                width: 100%;
                padding: 0 1rem;
                z-index: 999;
                background-color: #0e1117;
            }
        </style>
        """, unsafe_allow_html=True)

        st.text_input(
            "✍️ Escribe tu mensaje:",
            key="user_input",
            placeholder="Presiona Enter para enviar...",
            on_change=enviar_mensaje
        )

    # Botones flotantes al final
    with st.container():
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

        with col_btn1:
            if st.button("▶️ Enviar mensaje"):
                enviar_mensaje()

        with col_btn2:
            if st.button("💾 Guardar historial"):
                contenido_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Descargar JSON",
                    file_name="historial_chat.json",
                    mime="application/json",
                    data=contenido_json
                )

        with col_btn3:
            if st.button("☁️ Subir a Google Drive") and st.session_state.get("proyecto_id"):
                contenido_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2).encode("utf-8")
                nombre_archivo = "Historial_ChatGPT.json"
                enlace = subir_json_a_drive(nombre_archivo, contenido_json, st.session_state["proyecto_id"])
                if enlace:
                    st.success(f"✅ Subido correctamente: [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir el historial a Drive.")

        with col_btn4:
            if st.button("🧹 Borrar historial completo"):
                st.session_state.chat_history = []
                st.success("🧼 Historial borrado.")
