import streamlit as st
from bs4 import BeautifulSoup
import requests
import json

def render_scraping_urls_manuales():
    st.title("🧬 Scraping desde URLs pegadas manualmente")

    urls_input = st.text_area("🔗 Pega una o varias URLs (separadas por coma)", height=150, placeholder="https://example.com, https://otraweb.com")

    etiquetas = []
    col1, col2, col3, col4 = st.columns(4)
    with col1: title_check = st.checkbox("title")
    with col2: h1_check = st.checkbox("H1")
    with col3: h2_check = st.checkbox("H2")
    with col4: h3_check = st.checkbox("H3")

    if title_check: etiquetas.append("title")
    if h1_check: etiquetas.append("h1")
    if h2_check: etiquetas.append("h2")
    if h3_check: etiquetas.append("h3")

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
                if "h1" in etiquetas:
                    info["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")]
                if "h2" in etiquetas:
                    info["h2"] = [h.get_text(strip=True) for h in soup.find_all("h2")]
                if "h3" in etiquetas:
                    info["h3"] = [h.get_text(strip=True) for h in soup.find_all("h3")]

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
