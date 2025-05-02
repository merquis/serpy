import streamlit as st

# 🔧 Diccionario de etiquetas HTML con nombres visuales
etiquetas_html_dict = {
    "title": "Title",
    "meta[name='description']": "Descripción",
    "h1": "H1",
    "h2": "H2",
    "h3": "H3"
}

# 🔽 Lista de claves reales para el scraping
opciones_etiquetas = list(etiquetas_html_dict.keys())

# 🧬 Selector visual con nombres amigables
etiquetas_seleccionadas = st.multiselect(
    "🧬 Selecciona las etiquetas HTML que deseas extraer",
    options=opciones_etiquetas,
    default=opciones_etiquetas,
    format_func=lambda x: etiquetas_html_dict.get(x, x)
)

# 🛠️ Ahora puedes usar etiquetas_seleccionadas como antes:
# for etiqueta in etiquetas_seleccionadas:
#     resultado = soup.select(etiqueta)
