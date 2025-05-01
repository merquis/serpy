import streamlit as st
import json
import requests
from bs4 import BeautifulSoup

# ════════════════════════════════════════════════
# 🧩 MÓDULO: SCRAPING ETIQUETAS DESDE JSON CON URLS
# ════════════════════════════════════════════════

def render_scraping_etiquetas_url():
    st.title("🧬 Extraer etiquetas de URLs desde archivo JSON")

    uploaded_file = st.file_uploader("📁 Sube un archivo JSON con URLs obtenidas de Google", type="json")

    if uploaded_file:
        try:
            data = json.load(uploaded_file)
            st.success("✅ Archivo JSON cargado correctamente")

            resultados_finales = []
            etiquetas_seleccionadas = []
            col1, col2, col3 = st.columns(3)
            if col1.checkbox("H1"): etiquetas_seleccionadas.append("h1")
            if col2.checkbox("H2"): etiquetas_seleccionadas.append("h2")
            if col3.checkbox("H3"): etiquetas_seleccionadas.append("h3")

            if st.button("🚀 Extraer etiquetas"):
                with st.spinner("Procesando URLs y extrayendo etiquetas..."):
                    for entrada in data:
                        urls = entrada.get("urls", [])
                        etiqueta_resultado = {
                            "busqueda": entrada.get("busqueda"),
                            "urls": []
                        }
                        for url in urls:
                            resultado = {"url": url}
                            try:
                                res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                                soup = BeautifulSoup(res.text, 'html.parser')

                                resultado["title"] = soup.title.string.strip() if soup.title and soup.title.string else None
                                resultado["description"] = next((meta['content'] for meta in soup.find_all("meta") if meta.get("name", '').lower() == "description" and meta.get("content")), None)

                                for tag in etiquetas_seleccionadas:
                                    resultado[tag] = [h.text.strip() for h in soup.find_all(tag)]

                            except Exception as e:
                                resultado["error"] = str(e)

                            etiqueta_resultado["urls"].append(resultado)

                        resultados_finales.append(etiqueta_resultado)

                    st.subheader("📦 Resultados con etiquetas")
                    st.json(resultados_finales)

        except Exception as e:
            st.error(f"❌ Error al procesar el archivo JSON: {e}")
