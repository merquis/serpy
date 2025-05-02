def render_scraping_urls_manuales():
    import streamlit as st

    etiquetas_html_dict = {
        "title": "Title",
        "meta[name='description']": "Descripción",
        "h1": "H1",
        "h2": "H2",
        "h3": "H3"
    }

    opciones_etiquetas = list(etiquetas_html_dict.keys())

    etiquetas_seleccionadas = st.multiselect(
        "🧬 Selecciona las etiquetas HTML que deseas extraer",
        options=opciones_etiquetas,
        default=opciones_etiquetas,
        format_func=lambda x: etiquetas_html_dict.get(x, x)
    )

    st.write("✅ Etiquetas seleccionadas:", etiquetas_seleccionadas)
