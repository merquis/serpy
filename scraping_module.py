# ───────────────────────────────────────────────────────
# SERPY – Scraper Google con Streamlit + Proxy (BrightData)
# Versión 1.0.0 – Optimizada, rápida, sin duplicados ni JSON
# Autor: Merquis – Abril 2025
# ───────────────────────────────────────────────────────

import streamlit as st                     # Para crear interfaces web interactivas
import urllib.request                      # Para realizar solicitudes HTTP con soporte para proxy
import urllib.parse                        # Para codificar parámetros de búsqueda en URLs
from bs4 import BeautifulSoup              # Para analizar y extraer información del HTML de Google

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping con múltiples páginas
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results):
    """
    Realiza scraping de resultados de Google utilizando BrightData como proxy.
    Devuelve una lista de URLs de los primeros `num_results` resultados.
    """

    # Proxy configurado con credenciales de BrightData (zona serppy)
    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    
    # Google muestra 10 resultados por página
    step = 10

    # Lista donde se almacenarán las URLs extraídas
    urls = []

    # Recorremos las páginas necesarias hasta alcanzar `num_results`
    for start in range(0, num_results + step, step):
        if len(urls) >= num_results:
            break  # Si ya tenemos suficientes resultados, salimos

        # Codificamos la consulta para que sea compatible en la URL
        encoded_query = urllib.parse.quote(query)
        search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'

        try:
            # Creamos un "opener" con proxy configurado
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
            )

            # Realizamos la solicitud a Google con un timeout amplio (90 segundos)
            response = opener.open(search_url, timeout=90)

            # Leemos y decodificamos el contenido HTML
            html = response.read().decode('utf-8', errors='ignore')

            # Analizamos el HTML con BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # Seleccionamos todos los enlaces que contienen un <h3> (resultados orgánicos)
            enlaces_con_titulo = soup.select("a:has(h3)")

            # Recorremos los enlaces válidos y los agregamos a la lista
            for a in enlaces_con_titulo:
                if len(urls) >= num_results:
                    break  # Cortamos si alcanzamos el límite deseado
                href = a.get('href')
                if href and href.startswith("http"):
                    urls.append(href)

        except Exception as e:
            # Si hay error en una página (timeout, proxy, etc.), lo mostramos
            st.error(f"❌ Error al conectar con start={start}: {str(e)}")
            continue

    # ░░░ Mostrar solo URLs en texto plano
    if urls:
        st.subheader("🔗 Enlaces en texto plano")
        st.text("\n".join(urls))  # Mostramos las URLs separadas por saltos de línea
    else:
        st.warning("⚠️ No se encontraron enlaces estructurados.")
# ═══════════════════════════════════════════════
# 🖥️ INTERFAZ: GUI Streamlit con selector de resultados
# ═══════════════════════════════════════════════

def render_scraping():
    """
    Interfaz de usuario para ejecutar el scraping.
    Permite al usuario escribir una búsqueda y seleccionar el número de resultados.
    """

    # Título principal
    st.title("🔍 Scraping de Google (multiresultado con start)")

    # Dos columnas: una para la búsqueda, otra para el número de resultados
    col1, col2 = st.columns([3, 1])

    with col1:
        # Campo para escribir la búsqueda
        query = st.text_input("🔎 Escribe tu búsqueda en Google")

    with col2:
        # Selector desplegable para elegir la cantidad de resultados
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0)

    # Botón que lanza la búsqueda
    if st.button("Buscar") and query:
        with st.spinner("Consultando Google..."):
            testear_proxy_google(query, int(num_results))

