# scraping_urls_manuales.py
import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

# ════════════════════════════════════════════════
# 🌐 SCRAPING MANUAL DE UNA O VARIAS URLs
# ════════════════════════════════════════════════
def render_scraping_urls_manuales():
    st.title("🔗 Scrapear URLs manualmente")
    st.markdown("Pega una o varias URLs (separadas por coma o en líneas distintas).")

    entrada = st.text_area("🔗 URLs a scrapear", height=150, placeholder="https://ejemplo.com\nhttps://otro.com")

    etiquetas = []
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1: title_check = st.checkbox("Title", value=True)
    with col2: desc_check = st.checkbox("Descripción", value=True)
    with col3: h1_check = st.checkbox("H1")
    with col4: h2_check = st.checkbox("H2")
    with col5: h3_check = st.checkbox("H3")

    if title_check: etiquetas.append("title")
    if desc_check: etiquetas.append("description")
    if h1_check: etiquetas.append("h1")
    if h2_check: etiquetas.append("h2")
    if h3_check: etiquetas.append("h3")

    if not etiquetas:
        st.info("ℹ️ Selecciona al menos una etiqueta para extraer.")
        return

    if st.button("🔎 Extraer información") and entrada.strip():
        urls = [url.strip() for url in entrada.replace(",", "\n").splitlines() if url.strip()]
        resultados = []

        for url in urls:
            info = {"url": url}
            try:
                r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")

                if "title" in etiquetas:
                    info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None

                if "description" in etiquetas:
                    desc_tag = soup.find("meta", attrs={"name": "description"})
                    info["description"] = desc_tag["content"].strip() if desc_tag and "content" in desc_tag.attrs else None

                if "h1" in etiquetas:
                    info["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")]

                if "h2" in etiquetas:
                    info["h2"] = [h.get_text(strip=True) for h in soup.find_all("h2")]

                if "h3" in etiquetas:
                    info["h3"] = [h.get_text(strip=True) for h in soup.find_all("h3")]

            except Exception as e:
                info["error"] = str(e)

            resultados.append(info)

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="scraping_urls_manual.json",
            mime="application/json"
        )
