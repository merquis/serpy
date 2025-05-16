# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI
import json
# Importa tu nueva función específica de Drive
from modules.utils.drive_utils import subir_json_a_drive_especifico # <--- CAMBIO AQUÍ

def render_chat_libre():
    # ... (código de inicialización de OpenAI, session_state, obtención de ID de proyecto global) ...
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Asegúrate de configurar 'openai.api_key' en tus secrets.")
        return

    if "chat_libre_history" not in st.session_state:
        st.session_state.chat_libre_history = []
    
    id_proyecto_global_seleccionado = st.session_state.get("id_proyecto_drive_seleccionado", None)
    nombre_proyecto_global_seleccionado = st.session_state.get("nombre_proyecto_seleccionado", None) 
    modelo_gpt_global_seleccionado = st.session_state.get("modelo_gpt_seleccionado", "gpt-4o")

    with st.sidebar:
        st.subheader("Opciones del Chat Libre")

        id_proyecto_para_usar = None
        if nombre_proyecto_global_seleccionado and id_proyecto_global_seleccionado:
            st.success(f"Proyecto Activo: **{nombre_proyecto_global_seleccionado}**")
            id_proyecto_para_usar = id_proyecto_global_seleccionado 
        else:
            st.warning("⚠️ No hay un proyecto global seleccionado. La subida a Drive estará deshabilitada.")
            # No mostraremos el input manual si dependemos 100% de la selección global.

        # ... (selector de modelo como antes) ...
        modelos_disponibles = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        try:
            default_model_index = modelos_disponibles.index(modelo_gpt_global_seleccionado)
        except ValueError:
            default_model_index = 1 
        modelo_para_este_chat = st.selectbox(
            "🤖 Modelo para Chat Libre", 
            modelos_disponibles, 
            index=default_model_index, 
            key="chat_libre_model_selector_specific"
        )
        
        st.markdown("---")
        # ... (botón de guardar JSON) ...
        if st.button("💾 Guardar Historial (JSON)", key="chat_libre_save_json_button"):
            if st.session_state.chat_libre_history:
                contenido_json_str = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ Descargar JSON (Chat Libre)",
                    data=contenido_json_str,
                    file_name="historial_chat_libre.json",
                    mime="application/json",
                )
            else:
                st.info("No hay historial para guardar.")

        subir_a_drive_disabled = not id_proyecto_para_usar
        if st.button("☁️ Subir a Drive (Chat Libre)", disabled=subir_a_drive_disabled, key="chat_libre_upload_drive_button"):
            if st.session_state.chat_libre_history:
                timestamp_part = st.session_state.chat_libre_history[0]['content'][:15].replace(' ','_').replace('/', '_') if st.session_state.chat_libre_history else "vacio"
                nombre_historial_drive = f"Historial_ChatLibre_{timestamp_part}.json"
                
                contenido_json_bytes_drive = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2).encode("utf-8")
                
                # --- LLAMADA A LA FUNCIÓN ESPECÍFICA DE DRIVE ---
                enlace = subir_json_a_drive_especifico( # <--- USANDO LA NUEVA FUNCIÓN
                    nombre_archivo=nombre_historial_drive,
                    contenido_bytes=contenido_json_bytes_drive,
                    id_carpeta_proyecto_principal=id_proyecto_para_usar, # ID de "TripToIslands"
                    nombre_subcarpeta_destino="chat libre" # <--- AQUÍ ESPECIFICAS "chat libre"
                )
                if enlace:
                    st.success(f"✅ Historial subido a Drive. [Ver archivo]({enlace})")
                # El feedback de error ya lo da la función de Drive
            else:
                st.info("No hay historial para subir.")
        
        if subir_a_drive_disabled:
             st.caption("Selecciona un proyecto global para habilitar la subida a Drive.")
        
        # ... (botón de borrar historial) ...
        if st.button("🧹 Borrar Historial (Chat Libre)", type="primary", key="chat_libre_clear_button"):
            st.session_state.chat_libre_history = []
            st.success("🧼 Historial de Chat Libre borrado.")
            st.rerun()
            
    # ... (resto del código del chat: st.markdown, chat_container, st.chat_input, lógica de OpenAI) ...
    # Esto permanece igual
    st.markdown("### 📝 Historial de conversación")
    chat_container = st.container(height=400) 
    with chat_container:
        for mensaje in st.session_state.chat_libre_history:
            with st.chat_message(mensaje["role"]):
                st.markdown(mensaje['content'])

    if prompt := st.chat_input("Escribe tu mensaje aquí..."):
        st.session_state.chat_libre_history.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.spinner("GPT está escribiendo..."):
            try:
                response = client.chat.completions.create(
                    model=modelo_para_este_chat,
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_libre_history],
                    temperature=0.7,
                    max_tokens=1500,
                    stream=True
                )
                with chat_container:
                    with st.chat_message("assistant"):
                        full_response_content = st.write_stream(response)
                
                st.session_state.chat_libre_history.append({"role": "assistant", "content": full_response_content})
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error al contactar con OpenAI: {e}")
                error_msg = f"Error de API: {e}"
                st.session_state.chat_libre_history.append({"role": "assistant", "content": error_msg})
                with chat_container:
                     with st.chat_message("assistant"):
                        st.error(error_msg)
