# scraping_urls_manuales.py

import streamlit as st
import json
from scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url

# ════════════════════════════════════════════════
# 🧬 Extraer etiquetas desde URLs introducidas manualmente
# ════════════════════════════════════════════════
def render_scraping_urls_manuales():
    st.title("✍️ Extraer etiquetas SEO desde URLs manuales")
    st.markdown("Introduce una o más URLs (separadas por coma o línea nueva)")

    col1, col2 = st.columns([3, 1])
    with col1:
        input_urls = st.text_area("🌐 URLs a analizar", height=100, key="manual_input_urls")
    with col2:
        etiquetas = seleccionar_etiquetas_html()

    if not etiquetas:
        st.info("ℹ️ Selecciona al menos una etiqueta para extraer.")
        return

    if st.button("🔍 Extraer etiquetas") and input_urls:
        urls = [u.strip() for u in input_urls.replace("\n", ",").split(",") if u.strip()]
        if not urls:
            st.warning("⚠️ No se han encontrado URLs válidas.")
            return

        resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        nombre_salida = "etiquetas_urls_manuales.json"
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=nombre_salida,
            mime="application/json"
        )
