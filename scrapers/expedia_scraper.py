import streamlit as st
from scraper_tags_common import scrape_tags_from_url
import json

def render_scraping_expedia():
    st.title("🛫 Scraping Expedia")
    st.markdown("Pega una o varias URLs de Expedia (una por línea).")

    urls_raw = st.text_area("🔗 URLs de Expedia", height=200)
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

    if not urls:
        st.info("👆 Introduce al menos una URL para comenzar.")
        return

    if st.button("🔎 Scrapear"):
        resultados = []

        for url in urls:
            datos = scrape_tags_from_url(url)
            # 🧩 Aquí puedes añadir scraping específico de Expedia más adelante
            resultados.append(datos)

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="expedia_scraping.json",
            mime="application/json"
        )
