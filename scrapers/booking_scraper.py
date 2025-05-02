import streamlit as st
from scraper_tags_common import scrape_tags_from_url
import json

def render_scraping_booking():
    st.title("🏨 Scraping Booking.com")
    st.markdown("Pega una o varias URLs de Booking.com (una por línea).")

    urls_raw = st.text_area("🔗 URLs de Booking.com", height=200)
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

    if not urls:
        st.info("👆 Introduce al menos una URL para comenzar.")
        return

    if st.button("🔎 Scrapear"):
        resultados = []

        for url in urls:
            datos = scrape_tags_from_url(url)
            # 🧩 Aquí podrías añadir scraping específico de Booking más adelante.
            # Ejemplo: datos["precio_estimado"] = extraer_precio(soup)
            resultados.append(datos)

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="booking_scraping.json",
            mime="application/json"
        )
