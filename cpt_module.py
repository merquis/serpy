import streamlit as st

# ════════════════════════════════════════════════
# 🌐 INTERFAZ DEL MÓDULO CPT WORDPRESS
# ════════════════════════════════════════════════

def render_cpt_module():
    st.title("CPT Wordpress · Panel Admin")
    st.markdown("Este módulo servirá para crear y gestionar Custom Post Types en WordPress.")
    
    # Ejemplo visual de futura interfaz
    st.subheader("🧩 Crear nuevo CPT")

    with st.form("crear_cpt"):
        nombre_cpt = st.text_input("Nombre interno del CPT (slug)", placeholder="ej. alojamientos")
        nombre_singular = st.text_input("Nombre singular", placeholder="ej. Alojamiento")
        nombre_plural = st.text_input("Nombre plural", placeholder="ej. Alojamientos")
        descripcion = st.text_area("Descripción opcional")

        enviar = st.form_submit_button("Crear CPT")

        if enviar:
            if not nombre_cpt or not nombre_singular or not nombre_plural:
                st.warning("⚠️ Por favor completa todos los campos obligatorios.")
            else:
                st.success(f"✅ CPT '{nombre_plural}' ({nombre_cpt}) creado correctamente (simulado).")
                # Aquí en el futuro puedes conectar con WP REST API o guardar localmente
