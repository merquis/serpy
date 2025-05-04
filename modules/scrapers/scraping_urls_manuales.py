# scraping_urls_manuales.py

import streamlit as st
import json
from modules.utils.scraper_tags_common import seleccionar_etiquetas_html, scrape_tags_from_url


# ════════════════════════════════════════════════
# 🌐 Extraer etiquetas SEO desde URLs manuales
# ════════════════════════════════════════════════
def render_scraping_urls_manuales():
    st.title("🔗 Extraer etiquetas SEO desde URLs manuales")
    st.markdown("Introduce una o varias URLs separadas por coma o en líneas diferentes.")

    entrada_urls = st.text_area("🌍 URLs a analizar", height=100, placeholder="https://ejemplo1.com\nhttps://ejemplo2.com")

    if not entrada_urls:
        st.info("ℹ️ Introduce al menos una URL para comenzar.")
        return

    urls = [u.strip() for u in entrada_urls.replace(",", "\n").split("\n") if u.strip()]

    etiquetas = seleccionar_etiquetas_html()
    if not etiquetas:
        st.info("ℹ️ Selecciona al menos una etiqueta para extraer.")
        return

    if st.button("🔍 Extraer etiquetas"):
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
