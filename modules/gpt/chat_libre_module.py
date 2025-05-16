import streamlit as st
from openai import OpenAI
import json
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
from modules.gpt.analizador_archivos_module import procesar_archivo_subido


def render_chat_libre():
    st.title("💬 Chat libre con GPT (desde módulo)")
    st.markdown("Conversación sin restricciones, con historial, carga de archivos y subida a Drive.")

    # Inicializar cliente de OpenAI
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}")
        return

    # Estado inicial
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "archivo_contexto" not in st.session_state:
        st.session_state.archivo_contexto = None
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = st.sidebar.text_input("ID Proyecto Drive (Opcional)", key="chat_libre_project_id")
        if not st.session_state.proyecto_id:
            st.sidebar.warning("⚠️ No hay proyecto activo para Drive.")

    # Selector de modelo personalizado
    MODELOS_DISPONIBLES = [
        "gpt-3.5-turbo",
        "gpt-4o-mini",
        "gpt-4.1-nano",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4-turbo"
    ]
    indice_defecto = MODELOS_DISPONIBLES.index("gpt-4.1-mini")
    modelo_seleccionado = st.sidebar.selectbox(
        "🤖 Elige el modelo",
        options=MODELOS_DISPONIBLES,
        index=indice_defecto,
        key="chat_libre_model_select"
    )

    # Procesar archivos (OCR, PDFs, etc.)
    procesar_archivo_subido()

    # Mostrar historial de conversación
    st.markdown("### 📝 Historial de conversación")
    chat_container = st.container(height=400)
    with chat_container:
        for mensaje in st.session_state.chat_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje["content"])

    # Input de usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.spinner("GPT está escribiendo..."):
            try:
                mensajes_chat = []
                if st.session_state.get("archivo_contexto"):
                    mensajes_chat.append({
                        "role": "system",
                        "content": st.session_state["archivo_contexto"]
                    })
                mensajes_chat.extend(st.session_state.chat_history)

                response = client.chat.completions.create(
                    model=modelo_seleccionado,
                    messages=mensajes_chat,
                    temperature=0.7,
                    max_tokens=1500,
                    stream=True
                )
                with chat_container:
                    with st.chat_message("assistant"):
                        full_response_content = st.write_stream(response)

                st.session_state.chat_history.append({"role": "assistant", "content": full_response_content})
                st.rerun()

            except Exception as e:
                error_msg = f"❌ Error al contactar con OpenAI: {e}"
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                with chat_container:
                    with st.chat_message("assistant"):
                        st.error(error_msg)

    # Botones inferiores: Descargar, Subir, Borrar
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        contenido_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2) if st.session_state.chat_history else ""
        st.download_button(
            label="⬇️ Descargar JSON",
            file_name=f"historial_chat_{modelo_seleccionado}.json",
            mime="application/json",
            data=contenido_json,
            key="descargar_json_directo",
            disabled=not st.session_state.chat_history
        )

    with col_btn2:
        disabled_drive_button = not st.session_state.get("proyecto_id") or not st.session_state.chat_history
        if st.button("☁️ Subir a Google Drive", disabled=disabled_drive_button, key="chat_libre_upload_drive"):
            contenido_json = json.dumps(st.session_state.chat_history, ensure_ascii=False, indent=2).encode("utf-8")
            nombre_archivo = f"Historial_ChatGPT_{modelo_seleccionado}.json"
            subcarpeta_id = obtener_o_crear_subcarpeta("chat libre", st.session_state["proyecto_id"])
            if not subcarpeta_id:
                st.error("❌ No se pudo acceder o crear la subcarpeta 'chat libre'.")
                return

            enlace = subir_json_a_drive(nombre_archivo, contenido_json, carpeta_id=subcarpeta_id)
            if enlace:
                st.success(f"✅ Subido correctamente: [Ver en Drive]({enlace})")
            else:
                st.error("❌ Error al subir el historial a Drive.")

    with col_btn3:
        st.button(
            "🧹 Borrar Historial",
            type="primary",
            key="chat_libre_clear_history",
            on_click=lambda: st.session_state.update(chat_history=[], archivo_contexto=None),
            disabled=not st.session_state.chat_history
        )
