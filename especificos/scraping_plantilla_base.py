# especificos/scraping_plantilla_base.py
import streamlit as st
from scraper_tags_common import scrape_tags_from_url
import json

def render_scraping_nombre_dominio():
    st.title("🌐 Scraping NombreDominio.com")
    urls_raw = st.text_area("Pega URLs de NombreDominio.com", height=150)
    urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]

    if st.button("Scrapear NombreDominio"):
        resultados = []

        for url in urls:
            datos = scrape_tags_from_url(url)  # 🔁 ETIQUETAS COMUNES
            # 🧩 AQUÍ VA LO ESPECÍFICO DE CADA DOMINIO
            # Por ejemplo:
            # datos["precio"] = extraer_precio_personalizado(soup)
            # datos["valoracion"] = extraer_valoracion(url)
            resultados.append(datos)

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False),
            file_name="nombre_dominio_scraping.json",
            mime="application/json"
        )
