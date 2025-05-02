import streamlit as st
from scraper_tags_common import scrape_tags_from_url
import json

def render_scraping_amazon():
    st.title("🛒 Scraping Amazon")
    st.markdown("Pega una o varias URLs de Amazon (una por línea).")

    urls_raw = st.text_area("🔗 URLs de Amazon", height=200)
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

    if not urls:
        st.info("👆 Introduce al menos una URL para comenzar.")
        return

    if st.button("🔎 Scrapear"):
        resultados = []

        for url in urls:
            datos = scrape_tags_from_url(url)
            # 🧩 Aquí puedes añadir scraping específico de Amazon más adelante
            resultados.append(datos)

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="amazon_scraping.json",
            mime="application/json"
        )
