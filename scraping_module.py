import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import json
import requests
import ssl
from drive_utils import subir_json_a_drive

def testear_proxy_google(query, num_results, etiquetas_seleccionadas):
    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
    resultados_json = []
    terminos = [q.strip() for q in query.split(",") if q.strip()]
    ssl_context = ssl._create_unverified_context()

    for termino in terminos:
        urls_raw = []

        for start in range(0, num_results + step, step):
            if len(urls_raw) >= num_results:
                break

            encoded_query = urllib.parse.quote(termino)
            search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'

            try:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}),
                    urllib.request.HTTPSHandler(context=ssl_context)
                )
                response = opener.open(search_url, timeout=90)
                html = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, "html.parser")
                enlaces_con_titulo = soup.select("a:has(h3)")

                for a in enlaces_con_titulo:
                    if len(urls_raw) >= num_results:
                        break
                    href = a.get('href')
                    if href and href.startswith("http"):
                        urls_raw.append(href)

            except Exception as e:
                st.error(f"❌ Error conectando con '{termino}' (start={start}): {str(e)}")
                break

        urls_finales = []
        for url in urls_raw:
            try:
                res = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(res.text, 'html.parser')
                resultado = {
                    "url": url,
                    "title": soup.title.string.strip() if soup.title and soup.title.string else None,
                    "description": next((meta['content'] for meta in soup.find_all("meta") if meta.get("name", '').lower() == "description" and meta.get("content")), None)
                }

                for tag in ["h1", "h2", "h3"]:
                    if tag in etiquetas_seleccionadas:
                        resultado[tag] = [h.text.strip() for h in soup.find_all(tag)]

                urls_finales.append(resultado)

            except Exception as e:
                urls_finales.append({"url": url, "error": str(e)})

        resultados_json.append({
            "busqueda": termino,
            "urls": urls_finales
        })

    return resultados_json

def render_scraping():
    """
    Renderiza la interfaz para realizar el scraping.
    """
    st.title("TripToIslands · Panel Admin")

    if 'resultados' not in st.session_state:
        st.session_state.resultados = None
    if 'nombre_archivo' not in st.session_state:
        st.session_state.nombre_archivo = None
    if 'json_bytes' not in st.session_state:
        st.session_state.json_bytes = None

    # Selección del proyecto
    proyecto = st.sidebar.selectbox(
        "Seleccione proyecto:", 
        ["TripToIslands", "MiBebeBello"], 
        index=0,
        key="proyecto_selectbox"
    )

    carpeta_id = {
        "
