import streamlit as st
import urllib.request
import urllib.parse
import ssl
import json
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping con múltiples páginas y guardado en JSON
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results):
    ssl._create_default_https_context = ssl._create_unverified_context

    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10
    resultados = []
    raw_urls = []

    for start in range(0, num_results + step, step):
        encoded_query = urllib.parse.quote(query)
        search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'

        try:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
            )
            response = opener.open(search_url, timeout=30)
            html = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, "html.parser")

            # ░░░ Buscar todos los resultados de búsqueda (sin depender de clase)
            resultados_de_busqueda = soup.find_all('a', href=True)

            for a in resultados_de_busqueda:
                href = a.get('href')
                if href and href.startswith("http"):
                    # Obtener título si existe un <h3> relacionado
                    titulo = a.find_previous('h3')
                    titulo_texto = titulo.get_text(strip=True) if titulo else "Sin título"

                    # Intentar obtener la descripción de la página cercana
                    descripcion = a.find_next('div')
                    descripcion_texto = descripcion.get_text(strip=True) if descripcion else "Sin descripción"

                    # Añadir solo si es un enlace válido
                    if href:
                        resultados.append((titulo_texto, descripcion_texto, href))
                        raw_urls.append(href)

        except Exception as e:
            st.error(f"❌ Error al conectar con start={start}: {str(e)}")
            continue

    # Quitar duplicados y cortar al número solicitado
    resultados_unicos = []
    urls_vistas = set()
    for titulo, descripcion, url in resultados:
        if url not in urls_vistas:
            resultados_unicos.append((titulo, descripcion, url))
            urls_vistas.add(url)
        if len(resultados_unicos) >= num_results:
            break

    raw_urls_unicas = [url for _, _, url in resultados_unicos]

    # ░░░ Guardar resultados en un archivo JSON
    result_data = {
        "query": query,
        "results": [{"title": titulo, "description": descripcion, "url": url} for titulo, descripcion, url in resultados_unicos]
    }

    with open(f"{query}_results.json", "w", encoding="utf-8") as json_file:
        json.dump(result_data, json_file, ensure_ascii=False, indent=4)

    # ░░░ Mostrar resultados estructurados con título, descripción y link
    if resultados_unicos:
        st.subheader("🌐 Enlaces estructurados encontrados")
        for titulo, descripcion, url in resultados_unicos:
            st.markdown(f"**{titulo}**\n{descripcion}\n[{url}]({url})")
    else:
        st.warning("⚠️ No se encontraron enlaces estructurados.")

    # ░░░ Mostrar solo URLs en texto plano
    if raw_urls_unicas:
        st.subheader("🔗 Enlaces en texto plano")
        st.text("\n".join(raw_urls_unicas))

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI Streamlit con selector de resultados
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google (multiresultado con start)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google..."):
            testear_proxy_google(query, int(num_results))
