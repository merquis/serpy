import streamlit as st
import urllib.request
import urllib.parse
import ssl
import json
from bs4 import BeautifulSoup

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping con múltiples páginas y etiquetas SEO
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results, seo_tags):
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

            enlaces_con_titulo = soup.select("a:has(h3)")

            for a in enlaces_con_titulo:
                href = a.get('href')
                if href and href.startswith("http"):
                    resultados.append(href)
                    raw_urls.append(href)

        except Exception as e:
            st.error(f"❌ Error al conectar con start={start}: {str(e)}")
            continue

    # Quitar duplicados y cortar al número solicitado
    raw_urls_unicas = list(set(raw_urls))

    # ░░░ Entrar en cada URL y extraer etiquetas SEO seleccionadas
    extracted_data = []
    for url in raw_urls_unicas:
        try:
            response = opener.open(url, timeout=30)
            page_html = response.read().decode('utf-8', errors='ignore')
            page_soup = BeautifulSoup(page_html, "html.parser")

            page_data = {"url": url, "seo_tags": {}}
            
            for tag in seo_tags:
                tag_data = page_soup.find_all(tag)  # Buscar todas las etiquetas seleccionadas
                page_data["seo_tags"][tag] = [t.get_text(strip=True) for t in tag_data]

            extracted_data.append(page_data)

        except Exception as e:
            st.error(f"❌ Error al conectar con la URL {url}: {str(e)}")
            continue

    # Guardar resultados en JSON
    result_data = {
        "query": query,
        "results": extracted_data
    }

    with open(f"{query}_seo_results.json", "w", encoding="utf-8") as json_file:
        json.dump(result_data, json_file, ensure_ascii=False, indent=4)

    # ░░░ Mostrar resultados de SEO en texto plano
    if extracted_data:
        st.subheader("🌐 Resultados de SEO")
        for page in extracted_data:
            st.markdown(f"**URL**: {page['url']}")
            for tag, texts in page["seo_tags"].items():
                if texts:
                    st.markdown(f"**{tag.upper()}**:")
                    for text in texts:
                        st.markdown(f"- {text}")
                else:
                    st.markdown(f"*No se encontró {tag.upper()}.*")

    # ░░░ Mostrar solo URLs en texto plano
    if raw_urls_unicas:
        st.subheader("🔗 Enlaces en texto plano")
        st.text("\n".join(raw_urls_unicas))

# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI Streamlit con selector de resultados y etiquetas SEO
# ═══════════════════════════════════════════════

def render_scraping():
    st.title("🔍 Scraping de Google (multiresultado con start y etiquetas SEO)")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔎 Escribe tu búsqueda en Google")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    # ░░░ Selección de etiquetas SEO
    seo_tags = st.multiselect("🔑 Selecciona las etiquetas SEO", options=["h1", "h2", "h3", "h4"])

    if st.button("Buscar") and query:
        with st.spinner("Consultando Google..."):
            testear_proxy_google(query, int(num_results), seo_tags)
