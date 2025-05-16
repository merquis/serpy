# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI
import json

# --- Simulación de tu módulo de Drive para que el ejemplo sea autocontenido ---
def subir_json_a_drive_simulado(nombre_archivo, contenido_json_bytes, proyecto_id):
    """Simulación para el ejemplo."""
    if not proyecto_id:
        st.error("⚠️ ID del proyecto de Drive no especificado en la simulación.")
        return None
    # st.success(f"Simulando subida de '{nombre_archivo}' al proyecto '{proyecto_id}' de Drive...") # Evitar muchos mensajes de success
    print(f"Simulando subida de '{nombre_archivo}' al proyecto '{proyecto_id}' de Drive...")
    return f"https://drive.google.com/mock_link_for_{nombre_archivo.replace(' ', '_')}"
# --- Fin de la simulación ---

def render_chat_libre():
    st.header("💬 Chat Libre con GPT")
    st.markdown("Conversación sin restricciones, con historial, guardado y subida a Drive.")

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Asegúrate de configurar 'openai.api_key' en tus secrets.")
        return

    if "chat_libre_history" not in st.session_state:
        st.session_state.chat_libre_history = []
    
    if "chat_libre_project_id" not in st.session_state:
        st.session_state.chat_libre_project_id = ""


    with st.sidebar:
        st.subheader("Configuración Chat Libre")
        st.session_state.chat_libre_project_id = st.text_input(
            "ID Proyecto Drive (Chat Libre)", 
            value=st.session_state.chat_libre_project_id, 
            key="sidebar_chat_libre_project_id"
        )
        if not st.session_state.chat_libre_project_id:
            st.warning("⚠️ No hay proyecto activo para Drive en Chat Libre.")

        modelos = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        modelo_seleccionado_libre = st.selectbox(
            "🤖 Elige el modelo (Chat Libre)", 
            modelos, 
            index=1, 
            key="sidebar_chat_libre_model_select"
        )

        st.markdown("---")
        if st.button("💾 Guardar Historial (JSON)", key="sidebar_chat_libre_save_json"):
            if st.session_state.chat_libre_history:
                contenido_json = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Descargar JSON (Chat Libre)",
                    file_name="historial_chat_libre.json",
                    mime="application/json",
                    data=contenido_json
                )
            else:
                st.info("No hay historial en Chat Libre para guardar.")

        disabled_drive_button_libre = not st.session_state.chat_libre_project_id
        if st.button("☁️ Subir a Drive (Chat Libre)", disabled=disabled_drive_button_libre, key="sidebar_chat_libre_upload_drive"):
            if st.session_state.chat_libre_history:
                contenido_json_bytes = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2).encode("utf-8")
                nombre_archivo = "Historial_ChatLibre_GPT.json"
                enlace = subir_json_a_drive_simulado(nombre_archivo, contenido_json_bytes, st.session_state.chat_libre_project_id)
                if enlace:
                    st.success(f"✅ Subido (simulado): [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir a Drive (simulado).")
            else:
                st.info("No hay historial en Chat Libre para subir.")
        
        if st.button("🧹 Borrar Historial (Chat Libre)", type="primary", key="sidebar_chat_libre_clear_history"):
            st.session_state.chat_libre_history = []
            st.success("🧼 Historial de Chat Libre borrado.")
            st.rerun()

    # Historial de conversación
    chat_container = st.container(height=450)
    with chat_container:
        for mensaje in st.session_state.chat_libre_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje['content'])

    if prompt := st.chat_input("Escribe tu mensaje en el Chat Libre..."):
        st.session_state.chat_libre_history.append({"role": "user", "content": prompt})
        with chat_container: # Mostrar mensaje de usuario inmediatamente
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.spinner("GPT (Chat Libre) está escribiendo..."):
            try:
                response = client.chat.completions.create(
                    model=modelo_seleccionado_libre,
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_libre_history],
                    temperature=0.7,
                    max_tokens=2000,
                    stream=True
                )
                with chat_container: # Mostrar respuesta de asistente en streaming
                    with st.chat_message("assistant"):
                        full_response_content = st.write_stream(response)
                
                st.session_state.chat_libre_history.append({"role": "assistant", "content": full_response_content})
                # st.rerun() # write_stream y la siguiente interacción usualmente lo manejan

            except Exception as e:
                st.error(f"❌ Error con OpenAI (Chat Libre): {e}")
                error_msg = f"Error de API: {e}"
                st.session_state.chat_libre_history.append({"role": "assistant", "content": error_msg})
                with chat_container:
                     with st.chat_message("assistant"):
                        st.error(error_msg)
