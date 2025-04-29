import streamlit as st

def render():
    st.title("Relaciones entre CPTs (WordPress)")

    # Carga de secretos
    try:
        wp_user = st.secrets.get("wp_user", "")
        wp_password = st.secrets.get("wp_password", "")
    except Exception as e:
        st.warning(f"No se encontraron secretos de WordPress: {e}")
        wp_user = ""
        wp_password = ""

    st.write("Aquí iría la lógica para crear relaciones entre Custom Post Types.")
    st.write(f"Usuario WP cargado: {wp_user if wp_user else 'Ninguno'}")
