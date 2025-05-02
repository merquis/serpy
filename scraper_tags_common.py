# scraper_tags_common.py

import streamlit as st

def seleccionar_etiquetas_html():
    """
    Muestra un multiselect con las etiquetas HTML disponibles para extraer.
    Retorna una lista con los selectores HTML reales (no los nombres visibles).
    """

    # 🔄 Diccionario para mostrar nombres visuales amigables, pero devolver valores reales
    etiquetas_opciones = {
        "Title": "title",
        "Descripción": "meta[name='description']",
        "H1": "h1",
        "H2": "h2",
        "H3": "h3"
    }

    seleccion_visual = st.multiselect(
        "🧬 Selecciona las etiquetas HTML que deseas extraer",
        options=list(etiquetas_opciones.keys()),
        default=["Title", "Descripción", "H1", "H2", "H3"]
    )

    # 🔁 Devolver los valores reales según la selección
    etiquetas_reales = [etiquetas_opciones[nombre] for nombre in seleccion_visual]

    return etiquetas_reales
