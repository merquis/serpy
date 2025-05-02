
import streamlit as st

def obtener_opciones_etiquetas():
    return {
        "Title": "title",
        "Descripción": "meta[name='description']",
        "H1": "h1",
        "H2": "h2",
        "H3": "h3"
    }

def render_selector_etiquetas(clave_estado="etiquetas_html"):
    opciones = obtener_opciones_etiquetas()
    seleccionadas = st.multiselect(
        "🧪 Selecciona las etiquetas HTML que deseas extraer",
        options=list(opciones.keys()),
        format_func=lambda x: x,
        key=f"selector_{clave_estado}"
    )
    return [opciones[etiqueta] for etiqueta in seleccionadas]
