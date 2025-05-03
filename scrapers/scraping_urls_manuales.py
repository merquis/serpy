# scraping_urls_manuales.py

import streamlit as st
import json
from scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url

# ════════════════════════════════════════════════
# 🧬 Extraer etiquetas desde URLs pegadas manualmente
# ════════════════════════════════════════════════
def render_scraping_urls_manuales():
    st.title("🧬 Extraer etiquetas SEO desde URLs pegadas manualmente")
    st.markdown("Pega una o más URLs separadas por coma o línea nueva")

    urls_input = st.text_area("📥 Pega aquí las URLs", height=120, placeholder="https://ejemplo.com, https://otro.com")
    etiquetas = seleccionar_etiquetas_html()

    if not etiquetas:
        st.info("ℹ️ Selecciona al menos una etiqueta para extraer.")
        return

    if st.button("🔍 Extraer etiquetas"):
        if not urls_input.strip():
            st.warning("⚠️ No se han introducido URLs.")
            return

        # Separar por coma o salto de línea
        urls = [u.strip() for u in urls_input.replace("\n", ",").split(",") if u.strip()]

        resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        nombre_salida = "etiquetas_urls_pegadas.json"
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=nombre_salida,
            mime="application/json"
        )
