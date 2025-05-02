
import streamlit as st
from scraper_tags_common import scrape_tags_from_url, seleccionar_etiquetas_html
import json

def render_scraping_etiquetas_url():
    st.title("🧬 Scrapear etiquetas desde archivo JSON")
    archivo_subido = st.file_uploader("Sube archivo JSON con URLs", type="json")
    if not archivo_subido:
        return

    etiquetas = seleccionar_etiquetas_html()
    datos_json = json.load(archivo_subido)
    urls = []

    for entrada in datos_json:
        urls += entrada.get("urls", [])

    if st.button("🔎 Scrapear JSON"):
        resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]
        st.subheader("📦 Resultados")
        st.json(resultados)

        st.download_button("⬇️ Descargar JSON", json.dumps(resultados, indent=2, ensure_ascii=False),
                           "json_scraping.json", mime="application/json")


def render_scraping_urls_manuales():
    st.title("✍️ Scrapear URLs manualmente")
    entrada = st.text_area("🔗 Pega una o varias URLs (una por línea)", height=200)
    if not entrada:
        return

    etiquetas = seleccionar_etiquetas_html()
    urls = [u.strip() for u in entrada.splitlines() if u.strip()]

    if st.button("🔎 Scrapear manual"):
        resultados = [scrape_tags_from_url(url, etiquetas) for url in urls]
        st.subheader("📦 Resultados")
        st.json(resultados)

        st.download_button("⬇️ Descargar JSON", json.dumps(resultados, indent=2, ensure_ascii=False),
                           "manual_scraping.json", mime="application/json")
