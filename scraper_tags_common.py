import streamlit as st

def seleccionar_etiquetas_html():
    st.markdown("### 🏷️ Selecciona qué etiquetas deseas extraer")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: title_check = st.checkbox("title", value=True)
    with col2: desc_check = st.checkbox("description", value=True)
    with col3: h1_check = st.checkbox("h1")
    with col4: h2_check = st.checkbox("h2")
    with col5: h3_check = st.checkbox("h3")

    etiquetas = []
    if title_check: etiquetas.append("title")
    if desc_check: etiquetas.append("description")
    if h1_check: etiquetas.append("h1")
    if h2_check: etiquetas.append("h2")
    if h3_check: etiquetas.append("h3")

    if not etiquetas:
        st.warning("⚠️ Selecciona al menos una etiqueta para continuar.")
        st.stop()

    return etiquetas
