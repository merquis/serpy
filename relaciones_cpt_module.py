import streamlit as st

def render_sidebar():
    st.sidebar.header("🔧 Opciones CPT")
    st.sidebar.radio("Elige tipo de relación:", ["Hoteles", "Opiniones"], key="tipo_relacion")

def render():
    st.title("Relaciones CPT")
    st.write("Aquí iría el contenido principal del módulo de relaciones.")
