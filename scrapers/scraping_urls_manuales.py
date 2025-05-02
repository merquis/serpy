import streamlit as st
from scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url

def render_scraping_urls_manuales():
    st.header("🔗 Scrapear URLs introducidas manualmente")

    # Textarea para pegar las URLs
    urls_input = st.text_area("📥 Pega una o varias URLs (separadas por comas)", height=100)

    # Selector de etiquetas reutilizable
    etiquetas_seleccionadas = seleccionar_etiquetas_html()

    # Mostrar etiquetas seleccionadas
    if etiquetas_seleccionadas:
        st.success("✅ Etiquetas seleccionadas:")
        st.json(etiquetas_seleccionadas)

    # Ejecutar scraping
    if st.button("🚀 Iniciar scraping"):
        if not urls_input.strip():
            st.warning("⚠️ Introduce al menos una URL.")
            return

        urls = [url.strip() for url in urls_input.split(",") if url.strip()]
        if not urls:
            st.warning("⚠️ No se detectaron URLs válidas.")
            return

        with st.spinner("Procesando..."):
            resultados = []
            for url in urls:
                data = scrape_tags_from_url(url, etiquetas_seleccionadas)
                resultados.append(data)

            st.success("✅ Scraping completado")
            st.write(resultados)
