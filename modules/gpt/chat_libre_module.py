import streamlit as st
from openai import OpenAI
import json

# --- Simulación de tu módulo de Drive ---
# En un proyecto real, importarías tu módulo:
# from modules.utils.drive_utils import subir_json_a_drive

# Para que este script se pueda ejecutar de forma independiente, simulo la función:
def subir_json_a_drive(nombre_archivo, contenido_json_bytes, proyecto_id):
    """
    Simulación de la función para subir un JSON a Google Drive.
    En tu implementación real, esta función interactuaría con la API de Google Drive.
    """
    if not proyecto_id:
        st.error("⚠️ ID del proyecto de Drive no especificado.")
        return None
    print(f"Simulando subida de '{nombre_archivo}' al proyecto '{proyecto_id}' de Drive...")
    # Simula un retraso y devuelve un enlace falso
    import time
    time.sleep(1)
    return f"https://drive.google.com/mock_link_for_{nombre_archivo.replace(' ', '_')}"
# --- Fin de la simulación ---

def render_chat_mejorado():
    st.set_page_config(layout="wide", page_title="Chat GPT Mejorado") # Opcional: usar página ancha
    st.title("💬 Chat Avanzado con GPT")
    st.markdown("Conversación fluida con historial, guardado y subida a Drive. Las respuestas del asistente se muestran en tiempo real.")

    # --- Configuración en la Barra Lateral ---
    with st.sidebar:
        st.header("⚙️ Configuración y Acciones")

        # Inicializar el cliente de OpenAI
        # Es mejor manejar la posible ausencia de la API key con un try-except
        try:
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        except Exception as e:
            st.error(f"Error al inicializar el cliente de OpenAI. Verifica tu API key en los secrets: {e}")
            st.stop() # Detiene la ejecución si no se puede inicializar el cliente

        # Selección de Modelo
        modelos = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        selected_model = st.selectbox(
            "🤖 Elige el modelo GPT",
            modelos,
            index=1,  # gpt-4o por defecto (buen balance)
            help="gpt-3.5-turbo es más rápido y económico. gpt-4o y gpt-4-turbo ofrecen mayor calidad a un coste superior."
        )

        # Configuración del Proyecto de Drive
        if "proyecto_id" not in st.session_state:
            st.session_state.proyecto_id = None

        st.session_state.proyecto_id = st.text_input(
            "🆔 ID del Proyecto en Drive (Opcional)",
            value=st.session_state.get("proyecto_id", ""),
            placeholder="Pega aquí el ID de la carpeta de Drive",
            help="Necesario para poder subir el historial a Google Drive."
        )
        if not st.session_state.proyecto_id:
            st.warning("⚠️ No has especificado un ID de proyecto de Drive. La subida a Drive estará deshabilitada.")

        # Botones de Acción
        st.markdown("---")
        if st.button("💾 Guardar Historial (JSON)", help="Descarga el historial de chat actual como un archivo JSON."):
            if st.session_state.get("chat_history"):
                contenido_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Descargar Archivo JSON",
                    data=contenido_json,
                    file_name="historial_chat_gpt.json",
                    mime="application/json"
                )
                st.success("Historial listo para descargar.")
            else:
                st.info("ℹ️ No hay historial para guardar.")

        if st.button("☁️ Subir a Google Drive", disabled=not st.session_state.proyecto_id, help="Sube el historial de chat actual a la carpeta de Google Drive especificada."):
            if st.session_state.get("chat_history"):
                with st.spinner("Subiendo a Google Drive..."):
                    contenido_json_bytes = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2).encode("utf-8")
                    nombre_archivo = "Historial_ChatGPT.json"
                    enlace = subir_json_a_drive(nombre_archivo, contenido_json_bytes, st.session_state["proyecto_id"])
                    if enlace:
                        st.success(f"✅ Subido correctamente: [Ver en Drive]({enlace})")
                    else:
                        st.error("❌ Error al subir el historial a Drive. Verifica el ID del proyecto y los permisos.")
            else:
                st.info("ℹ️ No hay historial para subir.")

        st.markdown("---")
        if st.button("🧹 Borrar Historial Completo", type="primary", help="Elimina todos los mensajes del chat actual."):
            st.session_state.chat_history = []
            st.success("🧼 Historial borrado exitosamente.")
            st.rerun() # Forzar un rerun para limpiar la pantalla de mensajes

    # --- Lógica del Chat ---
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Mostrar mensajes del historial
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input del usuario
    if prompt := st.chat_input("✍️ Escribe tu mensaje aquí..."):
        # Añadir mensaje del usuario al historial y mostrarlo
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generar y mostrar respuesta del asistente con streaming
        with st.chat_message("assistant"):
            try:
                # Crear un generador para el stream de la API
                def stream_gpt_response():
                    stream = client.chat.completions.create(
                        model=selected_model,
                        messages=[
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.chat_history # Enviar todo el historial
                        ],
                        temperature=0.7,
                        max_tokens=2000, # Ajusta según necesidad
                        stream=True
                    )
                    for chunk in stream:
                        content_chunk = chunk.choices[0].delta.content
                        if content_chunk:
                            yield content_chunk

                # Usar st.write_stream para mostrar la respuesta en tiempo real
                # response_content guardará el mensaje completo una vez terminado el stream
                response_content = st.write_stream(stream_gpt_response)

                # Añadir respuesta completa del asistente al historial
                st.session_state.chat_history.append({"role": "assistant", "content": response_content})

            except Exception as e:
                st.error(f"❌ Error al contactar con OpenAI: {e}")
                # Opcionalmente, añadir un mensaje de error al historial del chat
                error_message = f"Error: No se pudo obtener respuesta. ({e})"
                st.session_state.chat_history.append({"role": "assistant", "content": error_message})
                # No es necesario un rerun aquí si el error se muestra en el chat_message actual
                # Pero si quieres que el error persista como un mensaje de chat, está bien.
                # st.rerun() # Puede ser útil si quieres que el estado se actualice completamente

# --- Ejecutar la aplicación ---
if __name__ == "__main__":
    # Para probar, necesitas configurar tus secrets de Streamlit con tu API key de OpenAI
    # Ejemplo: en un archivo .streamlit/secrets.toml
    # [openai]
    # api_key = "sk-..."

    # Si no tienes secrets configurados y quieres probarlo rápidamente (NO RECOMENDADO PARA PRODUCCIÓN):
    # import os
    # os.environ["OPENAI_API_KEY"] = "tu_api_key_aqui"
    # client = OpenAI() # OpenAI() sin api_key usa la variable de entorno

    render_chat_mejorado()
