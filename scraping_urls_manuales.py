import streamlit as st
from bs4 import BeautifulSoup
import requests
import json

def render_scraping_urls_manuales():
    st.title("🧬 Scraping desde URLs pegadas manualmente")

    urls_input = st.text_area("🔗 Pega una o varias URLs (separadas por coma)", height=150, placeholder="https://example.com, https://otraweb.com")

    etiquetas = []
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: title_check = st.checkbox("title")
    with col2: desc_check = st.checkbox("description")
    with col3: h1_check = st.checkbox("H1")
    with col4: h2_check = st.checkbox("H2")
    with col5: h3_check = st.checkbox("H3")
    with col6: h4_check = st.checkbox("H4")

    if title_check: etiquetas.append("title")
    if desc_check: etiquetas.append("description")
    if h1_check: etiquetas.append("h1")
    if h2_check: etiquetas.append("h2")
    if h3_check: etiquetas.append("h3")
    if h4_check: etiquetas.append("h4")

    if not etiquetas:
        st.info("ℹ️ Selecciona al menos una etiqueta para extraer.")
        return

    if st.button("🔎 Extraer etiquetas"):
        urls = [u.strip() for u in urls_input.split(",") if u.strip()]
        if not urls:
            st.warning("⚠️ No se han ingresado URLs válidas.")
            return

        resultados = []
        for url in urls:
            try:
                r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(r.text, "html.parser")
                info = {"url": url}

                if "title" in etiquetas:
                    info["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
                if "description" in etiquetas:
                    desc_tag = soup.find("meta", attrs={"name": "description"})
                    info["description"] = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else None
                if "h1" in etiquetas:
                    info["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")]
                if "h2" in etiquetas:
                    info["h2"] = [h.get_text(strip=True) for h in soup.find_all("h2")]
                if "h3" in etiquetas:
                    info["h3"] = [h.get_text(strip=True) for h in soup.find_all("h3")]
                if "h4" in etiquetas:
                    info["h4"] = [h.get_text(strip=True) for h in soup.find_all("h4")]

                resultados.append(info)

            except Exception as e:
                resultados.append({"url": url, "error": str(e)})

        st.subheader("📦 Resultados obtenidos")
        st.json(resultados)

        nombre_salida = "scraping_manual_urls.json"
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json.dumps(resultados, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=nombre_salida,
            mime="application/json"
        )
