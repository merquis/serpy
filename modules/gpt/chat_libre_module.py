# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI
import json

# --- Simulación de tu módulo de Drive (MODIFICADA) ---
def subir_json_a_drive_simulado(nombre_archivo_historial: str, contenido_json_bytes: bytes, id_proyecto_principal: str):
    """
    Simulación de subida a Drive.
    Ahora considera una subcarpeta conceptual "chat libre" dentro del proyecto principal.
    """
    if not id_proyecto_principal: # Si por alguna razón llega vacío, aunque no debería si hay selección.
        st.error("⚠️ ID del proyecto principal de Drive no proporcionado para la simulación.")
        return None
    
    ruta_conceptual_en_drive = f"Proyecto ID '{id_proyecto_principal}' / Carpeta 'chat libre' / {nombre_archivo_historial}"
    
    # Usamos st.info para que no sea tan intrusivo como st.success cada vez
    st.info(f"Simulación: Guardando '{nombre_archivo_historial}' en: {ruta_conceptual_en_drive}")
    print(f"Simulando subida de '{nombre_archivo_historial}' a: {ruta_conceptual_en_drive}")
    
    return f"https://drive.google.com/mock_link_to_project_{id_proyecto_principal.replace(' ', '_')}"
# --- Fin de la simulación ---


def render_chat_libre():
    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Asegúrate de configurar 'openai.api_key' en tus secrets.")
        return

    if "chat_libre_history" not in st.session_state:
        st.session_state.chat_libre_history = []
    
    # --- OBTENER EL ID DEL PROYECTO SELECCIONADO GLOBALMENTE ---
    # Este es el cambio clave. Asumimos que tu widget de navegación (el de image_7dba43.png)
    # guarda el ID del proyecto seleccionado en st.session_state.id_proyecto_drive_seleccionado
    # Y el nombre del proyecto en st.session_state.nombre_proyecto_seleccionado (para mostrarlo)
    
    id_proyecto_global_seleccionado = st.session_state.get("id_proyecto_drive_seleccionado", None)
    nombre_proyecto_global_seleccionado = st.session_state.get("nombre_proyecto_seleccionado", None)

    # --- OBTENER EL MODELO GPT SELECCIONADO GLOBALMENTE ---
    # Similarmente, si tienes un selector de modelo global.
    modelo_gpt_global_seleccionado = st.session_state.get("modelo_gpt_seleccionado", "gpt-4o") # Default a gpt-4o


    # ----- Controles en la Sidebar (Específicos para este módulo si es necesario) -----
    with st.sidebar:
        st.subheader("Opciones del Chat Libre")

        # Mostrar el proyecto activo si está seleccionado globalmente
        if nombre_proyecto_global_seleccionado and id_proyecto_global_seleccionado:
            st.success(f"Proyecto Activo: **{nombre_proyecto_global_seleccionado}**")
            # No necesitamos el input manual si ya hay uno global
            id_proyecto_para_usar = id_proyecto_global_seleccionado 
        else:
            # Fallback a input manual SI NO HAY NINGÚN PROYECTO GLOBAL SELECCIONADO
            st.warning("⚠️ No hay un proyecto global seleccionado.")
            id_proyecto_para_usar = st.text_input(
                 "ID Manual Proyecto Drive (Chat Libre)", 
                 value="", 
                 key="chat_libre_manual_project_id_input_fallback",
                 help="ID de la carpeta principal en Drive. El historial se guardará en una subcarpeta 'chat libre'."
            )
            if not id_proyecto_para_usar:
                 st.error("Se requiere un proyecto para la subida a Drive.")


        # Selector de modelo específico para este chat, o usar el global.
        modelos_disponibles = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        # Intentar preseleccionar con el global, si existe en la lista de este chat
        try:
            default_model_index = modelos_disponibles.index(modelo_gpt_global_seleccionado)
        except ValueError:
            default_model_index = 1 # gpt-4o

        modelo_para_este_chat = st.selectbox(
            "🤖 Modelo para Chat Libre", 
            modelos_disponibles, 
            index=default_model_index, 
            key="chat_libre_model_selector_specific"
        )
        
        st.markdown("---")
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

        subir_a_drive_disabled = not id_proyecto_para_usar # Se deshabilita si no hay ID (ni global ni manual)
        if st.button("☁️ Subir a Drive (Chat Libre)", disabled=subir_a_drive_disabled, key="chat_libre_upload_drive_button"):
            if st.session_state.chat_libre_history:
                # Generar un nombre de archivo un poco más único/descriptivo
                timestamp = json.dumps(st.session_state.chat_libre_history[0]['content'][:20].replace(' ','_')) if st.session_state.chat_libre_history else "vacio"
                nombre_historial = f"Historial_ChatLibre_{timestamp}.json"
                
                contenido_json_bytes_drive = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2).encode("utf-8")
                
                enlace = subir_json_a_drive_simulado(
                    nombre_archivo_historial=nombre_historial,
                    contenido_json_bytes=contenido_json_bytes_drive,
                    id_proyecto_principal=id_proyecto_para_usar # Usar el ID determinado
                )
                # El feedback de éxito/error ya lo da la función simulada o la real.
            else:
                st.info("No hay historial para subir.")
        
        if subir_a_drive_disabled:
             st.caption("Selecciona un proyecto global o ingresa un ID manual para habilitar la subida a Drive.")

        if st.button("🧹 Borrar Historial (Chat Libre)", type="primary", key="chat_libre_clear_button"):
            st.session_state.chat_libre_history = []
            st.success("🧼 Historial de Chat Libre borrado.")
            st.rerun()

    # ----- Cuerpo Principal del Chat -----
    # (El resto del código del chat principal no necesita cambios significativos para esto)
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
