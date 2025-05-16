# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI # Asegúrate de que OpenAI esté importado si lo usas aquí
import json

# Si 'subir_json_a_drive' viene de otro módulo tuyo, por ejemplo 'modules.utils.drive_utils'
# deberías importarlo aquí si esta función lo usa directamente.
# Ejemplo: from modules.utils.drive_utils import subir_json_a_drive
# Para este ejemplo, asumiré que la función original que me diste para el chat libre es la que va aquí.

# --- Simulación de tu módulo de Drive para que el ejemplo sea autocontenido ---
# En un proyecto real, importarías tu módulo:
# from modules.utils.drive_utils import subir_json_a_drive

def subir_json_a_drive_simulado(nombre_archivo, contenido_json_bytes, proyecto_id):
    """Simulación para el ejemplo."""
    if not proyecto_id:
        st.error("⚠️ ID del proyecto de Drive no especificado en la simulación.")
        return None
    st.success(f"Simulando subida de '{nombre_archivo}' al proyecto '{proyecto_id}' de Drive...")
    return f"https://drive.google.com/mock_link_for_{nombre_archivo.replace(' ', '_')}"
# --- Fin de la simulación ---


def render_chat_libre(): # ESTA ES LA FUNCIÓN QUE SE IMPORTARÁ
    st.title("💬 Chat libre con GPT (desde módulo)")
    st.markdown("Conversación sin restricciones, con historial, guardado y subida a Drive.")

    # Inicializar el cliente de OpenAI
    # Asegúrate de que tus secrets están configurados en Streamlit Cloud o localmente
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Asegúrate de configurar 'openai.api_key' en tus secrets.")
        return # Salir si no se puede inicializar

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Manejo del proyecto_id (puedes mover esto a la sidebar en streamlit_app.py si es global)
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = st.sidebar.text_input("ID Proyecto Drive (Opcional)", key="chat_libre_project_id")
        if not st.session_state.proyecto_id:
            st.sidebar.warning("⚠️ No hay proyecto activo para Drive.")


    modelos = [
        "gpt-3.5-turbo",
        "gpt-4o",
        "gpt-4-turbo"
    ]
    # Puedes poner el selectbox en la sidebar de la app principal o aquí
    modelo_seleccionado = st.sidebar.selectbox("🤖 Elige el modelo (Chat Libre)", modelos, index=1, key="chat_libre_model_select")


    # Historial de conversación
    st.markdown("### 📝 Historial de conversación")
    chat_container = st.container(height=400) # Contenedor con scroll para el chat
    with chat_container:
        for mensaje in st.session_state.chat_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje['content'])

    # Input del usuario usando st.chat_input
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        # Actualizar el chat_container inmediatamente con el mensaje del usuario
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.spinner("GPT está escribiendo..."):
            try:
                # Usar el modelo seleccionado en la sidebar
                response = client.chat.completions.create(
                    model=modelo_seleccionado,
                    messages=st.session_state.chat_history,
                    temperature=0.7,
                    max_tokens=1500,
                    stream=True # Habilitar streaming
                )

                # Mostrar respuesta en streaming
                with chat_container:
                    with st.chat_message("assistant"):
                        full_response_content = st.write_stream(response) # Esto muestra y recoge la respuesta

                st.session_state.chat_history.append({"role": "assistant", "content": full_response_content})
                st.rerun() # Rerun para asegurar que el historial se actualice visualmente si es necesario

            except Exception as e:
                st.error(f"❌ Error al contactar con OpenAI: {e}")
                # Opcionalmente añadir el error al historial
                error_msg = f"Error de API: {e}"
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                with chat_container: # Mostrar el error en el chat también
                     with st.chat_message("assistant"):
                        st.error(error_msg)


    # Acciones (puedes moverlas a una sidebar si prefieres)
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("💾 Guardar Historial (JSON)", key="chat_libre_save_json"):
            if st.session_state.chat_history:
                contenido_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Descargar JSON",
                    file_name="historial_chat_libre.json",
                    mime="application/json",
                    data=contenido_json
                )
            else:
                st.info("No hay historial para guardar.")

    with col_btn2:
        disabled_drive_button = not st.session_state.get("proyecto_id")
        if st.button("☁️ Subir a Google Drive", disabled=disabled_drive_button, key="chat_libre_upload_drive"):
            if st.session_state.chat_history:
                contenido_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2).encode("utf-8")
                nombre_archivo = "Historial_ChatGPT_Libre.json"
                # Usa tu función real aquí, o la simulada para el ejemplo
                enlace = subir_json_a_drive_simulado(nombre_archivo, contenido_json, st.session_state["proyecto_id"])
                if enlace:
                    st.success(f"✅ Subido correctamente (simulado): [Ver en Drive]({enlace})")
                else:
                    st.error("❌ Error al subir el historial a Drive (simulado).")
            else:
                st.info("No hay historial para subir.")
        elif disabled_drive_button:
            st.caption("Habilita la subida a Drive ingresando un ID de Proyecto.")


    with col_btn3:
        if st.button("🧹 Borrar Historial", type="primary", key="chat_libre_clear_history"):
            st.session_state.chat_history = []
            st.success("🧼 Historial borrado.")
            st.rerun() # Para refrescar la vista del historial

# Puedes tener otras funciones aquí si lo necesitas, pero render_chat_libre debe estar definida.
# def otra_funcion_ayudante():
#     pass
