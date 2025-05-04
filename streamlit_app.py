import streamlit as st
from drive_utils import obtener_subcarpetas_drive, crear_carpeta_en_drive

with st.sidebar.expander("📁 Selecciona o crea un proyecto", expanded=False):
    if "proyecto_id" not in st.session_state:
        st.session_state.proyecto_id = None
        st.session_state.proyecto_nombre = None
        st.session_state.nuevo_proyecto_creado = False

    try:
        carpetas = obtener_subcarpetas_drive()
        nombres = list(carpetas.keys())
        seleccionado = st.selectbox("📂 Proyecto activo", nombres)

        if seleccionado:
            st.session_state.proyecto_id = carpetas[seleccionado]
            st.session_state.proyecto_nombre = seleccionado
            st.success(f"📌 Proyecto seleccionado: {seleccionado}")

    except Exception as e:
        st.error(f"Error al obtener subcarpetas: {e}")

    # Crear nuevo proyecto
    if st.button("➕ Crear nuevo proyecto"):
        st.session_state.nuevo_proyecto_creado = True

    if st.session_state.get("nuevo_proyecto_creado", False):
        nuevo_nombre = st.text_input("📌 Nombre del nuevo proyecto")
        if st.button("✅ Confirmar creación"):
            nuevo_id = crear_carpeta_en_drive(nuevo_nombre)
            st.session_state.proyecto_id = nuevo_id
            st.session_state.proyecto_nombre = nuevo_nombre
            st.session_state.nuevo_proyecto_creado = False
            st.rerun()
