# modules/gpt/chat_libre_module.py

import streamlit as st
from openai import OpenAI # Asegúrate de que OpenAI esté importado si lo usas aquí
import json
# NO necesitas las importaciones de asyncio, playwright, beautifulsoup, etc., aquí
# si este módulo es solo para el chat libre.

# --- Simulación de tu módulo de Drive (MODIFICADA) ---
def subir_json_a_drive_simulado(nombre_archivo_historial: str, contenido_json_bytes: bytes, id_proyecto_principal: str):
    """
    Simulación de subida a Drive.
    Ahora considera una subcarpeta conceptual "chat libre" dentro del proyecto principal.
    """
    if not id_proyecto_principal:
        st.error("⚠️ ID del proyecto principal de Drive no especificado en la simulación.")
        return None
    
    # Conceptual: dónde se guardaría el archivo
    ruta_conceptual_en_drive = f"Proyecto '{id_proyecto_principal}' / Carpeta 'chat libre' / {nombre_archivo_historial}"
    
    st.success(f"Simulando subida de '{nombre_archivo_historial}' a: {ruta_conceptual_en_drive}")
    print(f"Simulando subida de '{nombre_archivo_historial}' a: {ruta_conceptual_en_drive}") # Para la consola
    
    # El enlace podría ser a la carpeta principal o un mock al archivo
    return f"https://drive.google.com/mock_link_to_project_{id_proyecto_principal.replace(' ', '_')}"
# --- Fin de la simulación ---


def render_chat_libre():
    # El título y markdown ya están en streamlit_app.py cuando se selecciona este módulo.
    # Aquí podrías poner un subtítulo si quieres, o nada.
    # st.header("💬 Chat Libre con GPT") # Puedes quitarlo si ya está en la app principal
    # st.markdown("Conversación sin restricciones, con historial, guardado y subida a Drive.")

    try:
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    except Exception as e:
        st.error(f"Error al inicializar OpenAI: {e}. Asegúrate de configurar 'openai.api_key' en tus secrets.")
        return

    # Usar claves de session_state específicas para este módulo para evitar colisiones
    if "chat_libre_history" not in st.session_state:
        st.session_state.chat_libre_history = []
    
    # El ID del proyecto principal y el modelo se configuran en la sidebar de streamlit_app.py
    # o se pasan como argumentos a esta función si quieres más modularidad.
    # Por ahora, asumimos que se leen de st.session_state si fueron configurados en la app principal.

    # Referencia al ID del proyecto principal y modelo seleccionado (configurados en la app principal)
    # Estos valores deberían ser establecidos por tu widget de selección de proyecto global o el text_input
    # que estaba en la versión anterior del código completo que te di.
    # Por ejemplo, en streamlit_app.py, cuando seleccionas un proyecto, guardas su ID en:
    # st.session_state.id_proyecto_drive_seleccionado = "ID_DEL_PROYECTO_REAL_O_NOMBRE"
    
    id_proyecto_drive_actual = st.session_state.get("id_proyecto_drive_seleccionado", "") # Obtener de la app principal
    modelo_seleccionado_actual = st.session_state.get("modelo_gpt_seleccionado", "gpt-4o") # Obtener de la app principal


    # ----- Controles en la Sidebar (Específicos para este módulo si es necesario) -----
    # Si el ID del proyecto y el modelo son globales, estos controles podrían estar en streamlit_app.py
    # Si son específicos para este chat, pueden estar aquí.
    # Por simplicidad, y para alinearlo con el código anterior, los pondré aquí,
    # pero idealmente el ID del proyecto es global.

    with st.sidebar:
        st.subheader("Opciones del Chat Libre")
        # Si ya tienes un selector de proyecto global, no necesitas este input aquí.
        # Si no, este es el input manual:
        if not id_proyecto_drive_actual: # Solo mostrar si no hay uno global seleccionado
             id_proyecto_drive_actual = st.text_input(
                 "ID Manual Proyecto Drive (Chat Libre)", 
                 value=id_proyecto_drive_actual, 
                 key="chat_libre_manual_project_id_input",
                 help="ID de la carpeta principal en Drive. El historial se guardará en una subcarpeta 'chat libre'."
             )

        if not id_proyecto_drive_actual:
            st.warning("⚠️ No hay proyecto activo para Drive. Ingrese un ID o seleccione un proyecto.")
        
        # Selector de modelo específico para este chat, si se desea.
        # O usar el 'modelo_seleccionado_actual' global.
        modelos_disponibles = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
        modelo_para_este_chat = st.selectbox(
            "🤖 Modelo para Chat Libre", 
            modelos_disponibles, 
            index=modelos_disponibles.index(modelo_seleccionado_actual) if modelo_seleccionado_actual in modelos_disponibles else 1, 
            key="chat_libre_model_selector_specific"
        )
        
        st.markdown("---")
        # Botones de acción para el historial de este chat
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

        # Botón de subir a Drive
        subir_a_drive_disabled = not id_proyecto_drive_actual
        if st.button("☁️ Subir a Drive (Chat Libre)", disabled=subir_a_drive_disabled, key="chat_libre_upload_drive_button"):
            if st.session_state.chat_libre_history:
                contenido_json_bytes_drive = json.dumps(st.session_state.chat_libre_history, ensure_ascii=False, indent=2).encode("utf-8")
                nombre_historial = f"Historial_ChatLibre_{json.loads(contenido_json_bytes_drive)[0]['content'][:20].replace(' ','_') if st.session_state.chat_libre_history else 'vacio'}.json"
                
                enlace = subir_json_a_drive_simulado(
                    nombre_archivo_historial=nombre_historial,
                    contenido_json_bytes=contenido_json_bytes_drive,
                    id_proyecto_principal=id_proyecto_drive_actual 
                )
                if enlace:
                    st.success(f"✅ Historial subido (simulado).") # El detalle ya está en la función simulada
                else:
                    st.error("❌ Error al simular subida a Drive.")
            else:
                st.info("No hay historial para subir.")
        
        if subir_a_drive_disabled:
             st.caption("Selecciona o ingresa un proyecto para habilitar la subida a Drive.")

        if st.button("🧹 Borrar Historial (Chat Libre)", type="primary", key="chat_libre_clear_button"):
            st.session_state.chat_libre_history = []
            st.success("🧼 Historial de Chat Libre borrado.")
            st.rerun()


    # ----- Cuerpo Principal del Chat -----
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
                    model=modelo_para_este_chat, # Usar el modelo seleccionado para este chat
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_libre_history],
                    temperature=0.7,
                    max_tokens=1500,
                    stream=True
                )
                with chat_container:
                    with st.chat_message("assistant"):
                        full_response_content = st.write_stream(response)
                
                st.session_state.chat_libre_history.append({"role": "assistant", "content": full_response_content})
                st.rerun() # Para que el historial se muestre correctamente tras el stream

            except Exception as e:
                st.error(f"❌ Error al contactar con OpenAI: {e}")
                error_msg = f"Error de API: {e}"
                st.session_state.chat_libre_history.append({"role": "assistant", "content": error_msg})
                with chat_container:
                     with st.chat_message("assistant"):
                        st.error(error_msg)

# --- El resto del código (Scraping Booking) NO debería estar en este archivo ---
# --- si este archivo es solo para el módulo de "Chat Libre". ---
# --- Deberías moverlo a su propio módulo, por ejemplo: ---
# --- modules/scrapers/booking_scraper_module.py ---

# Ejemplo de cómo tu streamlit_app.py podría manejar la selección de proyecto y modelo:
#
# En streamlit_app.py:
#
# project_list = {"TripToIslands": "ID_DRIVE_TRIPTOISLANDS", "OtroProyecto": "ID_DRIVE_OTROPROYECTO"}
# selected_project_name = st.sidebar.selectbox("Seleccione proyecto:", list(project_list.keys()))
# st.session_state.id_proyecto_drive_seleccionado = project_list[selected_project_name]
#
# modelos_globales = ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"]
# st.session_state.modelo_gpt_seleccionado = st.sidebar.selectbox("Modelo GPT Global:", modelos_globales)
#
# if app_mode == "Chat Libre":
#     # render_chat_libre() ya no necesitaría configurar el ID del proyecto ni el modelo
#     # si los toma de st.session_state como he sugerido arriba.
#     render_chat_libre()
