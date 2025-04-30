# ───────────────────────────────────────────────────────
# SERPY – Scraper Google con Streamlit + Proxy (BrightData)
# Versión 1.0.0 – Rápida, optimizada, sin JSON, sin duplicados
# Última modificación por Merquis – Abril 2025
# ───────────────────────────────────────────────────────

import streamlit as st                     # Framework para construir interfaces web interactivas
import urllib.request                      # Módulo para realizar solicitudes HTTP
import urllib.parse                        # Para codificar correctamente los términos de búsqueda
from bs4 import BeautifulSoup              # Librería para parsear y navegar HTML (scraping)

# ═══════════════════════════════════════════════════════
# 🔍 FUNCIONALIDAD PRINCIPAL: Scraping de Google paginado
# ═══════════════════════════════════════════════════════

def testear_proxy_google(query, num_results):
    """
    Realiza scraping de Google utilizando proxy de BrightData.
    Obtiene los primeros `num_results` enlaces de resultados orgánicos (con título h3).
    """

    # URL del proxy BrightData (Zona: serppy)
    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'

    step = 10              # Número de resultados que Google muestra por página
    urls = []              # Lista final donde se almacenarán las URLs extraídas

    # Paginación para recorrer resultados (Google usa el parámetro start=)
    for start in range(0, num_results + step, step):
        if len(urls) >= num_results:
            break  # Si ya tenemos suficientes resultados, salimos del bucle

        # Codificar la búsqueda para usarla en una URL
        encoded_query = urllib.parse.quote(query)
        search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'

        try:
            # Configurar la conexión con el proxy
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
            )

            # Hacer la solicitud con timeout amplio (90 segundos)
            response = opener.open(search_url, timeout=90)

            # Leer y parsear el HTML devuelto
            html = response.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, "html.parser")

            # Buscar enlaces que contienen un <h3> (característico de resultados orgánicos)
            enlaces_con_titulo = soup.select("a:has(h3)")

            # Extraer los href de cada enlace
            for a in enlaces_con_titulo:
                if len(urls) >= num_results:
                    break  # Cortamos si alcanzamos el número deseado
                href = a.get('href')
                if href and href.startswith("http"):
                    urls.append(href)

        except Exception as e:
            st.error(f"❌ Error al conectar con start={start}: {str(e)}")
            continue  # Si hay error en una página, pasamos a la siguiente

    # ═══════════════════════════════════════════════
    # 🔗 MOSTRAR RESULTADOS EN PANTALLA (sólo texto plano)
    # ═══════════════════════════════════════════════

    if urls:
        st.subheader("🔗 Enlaces en texto plano")
        st.text("\n".join(urls))
    else:
        st.warning("⚠️ No se encontraron enlaces estructurados.")
