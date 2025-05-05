import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from modules.utils.drive_utils import subir_json_a_drive

def extraer_etiquetas(url):
    try:
        response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        status_code = response.status_code

        if response.status_code != 200:
            return {"url": url, "status_code": status_code}

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string.strip() if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag["content"].strip() if description_tag and "content" in description_tag.attrs else ""

        h1 = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        h2 = [tag.get_text(strip=True) for tag in soup.find_all("h2")]
        h3 = [tag.get_text(strip=True) for tag in soup.find_all("h3")]

        return {
            "url": url,
            "title": title,
            "description": description,
            "h1": h1,
            "h2": h2,
            "h3": h3,
            "status_code": status_code
        }

    except Exception as e:
        return {"url": url, "status_code": "error", "error": str(e)}

def render_scraping_etiquetas_json():
    st.title("🔎 Scrapear etiquetas desde JSON de URLs")

    archivo = st.file_uploader("📁 Sube el archivo JSON generado por el scraper de Google", type=["json"])
    if archivo:
        data = json.load(archivo)

        if not isinstance(data, list) or not data or "urls" not in data[0]:
            st.error("❌ El archivo no tiene el formato esperado.")
            return

        st.success(f"✅ {len(data)} bloque(s) cargado(s).")

        # Mostrar info de contexto (búsqueda, idioma, etc.)
        primer_bloque = data[0]
        st.subheader("📄 Detalles de la búsqueda original")
        st.markdown(f"""
        - **🧭 Búsqueda:** `{primer_bloque.get('busqueda', 'N/A')}`
        - **🌐 Idioma (`hl`)**: `{primer_bloque.get('idioma', 'N/A')}`
        - **📍 Región (`gl`)**: `{primer_bloque.get('region', 'N/A')}`
        - **🧭 Dominio**: `{primer_bloque.get('dominio', 'N/A')}`
        - **🔗 URL de búsqueda**: [{primer_bloque.get('url_busqueda', '')}]({primer_bloque.get('url_busqueda', '')})
        """)

        if st.button("🚀 Iniciar scraping de etiquetas"):
            resultados = []
            with st.spinner("Procesando..."):
                for bloque in data:
                    contexto = {
                        "busqueda": bloque.get("busqueda", ""),
                        "idioma": bloque.get("idioma", ""),
                        "region": bloque.get("region", ""),
                        "dominio": bloque.get("dominio", ""),
                        "url_busqueda": bloque.get("url_busqueda", "")
                    }
                    for url in bloque.get("urls", []):
                        resultado = extraer_etiquetas(url)
                        resultado_completo = {**contexto, **resultado}
                        resultados.append(resultado_completo)

            st.success("✅ Scraping finalizado.")
            st.subheader("📦 Resultado en JSON")
            st.json(resultados)

            nombre_archivo = "scraping_etiquetas_resultado.json"
            json_bytes = json.dumps(resultados, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("⬇️ Descargar JSON", data=json_bytes, file_name=nombre_archivo, mime="application/json")

            if st.button("☁️ Subir a Google Drive") and st.session_state.get("proyecto_id"):
                enlace = subir_json_a_drive(nombre_archivo, json_bytes, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Subido correctamente: [Ver archivo]({enlace})", icon="📁")
