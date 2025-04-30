# ───────────────────────────────────────────────────────
# SERPY – Scraper Google con Streamlit + Proxy (BrightData)
# Versión 1.0.0 – Optimizada, rápida, sin duplicados ni JSON
# Autor: Merquis – Abril 2025
# ───────────────────────────────────────────────────────

import streamlit as st                     # Para crear interfaces interactivas en la web
import urllib.request                      # Para hacer solicitudes HTTP (con proxy configurado)
import urllib.parse                        # Para codificar parámetros en URLs
from bs4 import BeautifulSoup              # Para analizar y extraer contenido del HTML de Google

# ═══════════════════════════════════════════════
# 🔧 FUNCIONALIDAD: Scraping con múltiples páginas
# ═══════════════════════════════════════════════

def testear_proxy_google(query, num_results):
    """
    Realiza scraping de resultados de Google utilizando BrightData como proxy.
    Devuelve una lista de URLs de los primeros `num_results` resultados.
    """

    # Configuración del proxy BrightData (zona: serppy)
    proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-serppy:o20gy6i0jgn4@brd.superproxy.io:33335'
    step = 10            # Google muestra 10 resultados por página
    urls = []            # Lista para almacenar las URLs encontradas

    # Iteramos por las páginas de resultados necesarias para alcanzar `num_results`
    for start in range(0, num_results + step, step):
        if len(urls) >= num_results:
            break  # Si ya tenemos suficientes resultados, salimos del bucle

        # Codificamos la consulta para construir una URL segura
        encoded_query = urllib.parse.quote(query)
        search_url = f'https://www.google.com/search?q={encoded_query}&start={start}'

        try:
            # Configuración del "opener" para usar el proxy BrightData
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({
                    'http': proxy_url,
                    'https': proxy_url
                })
            )

            # Realizamos la solicitud a Google con un timeout amplio (90 segundos)
            response = opener.open(search_url, timeout=90)

            # Leemos el HTML de la respuesta y lo convertimos en texto
            html = response.read().decode('utf-8', errors='ignore')

            # Usamos BeautifulSoup para analizar el HTML
            soup = BeautifulSoup(html, "html.parser")

            # Seleccionamos solo los enlaces que contienen un <h3> (resultados orgánicos)
            enlaces_con_titulo = soup.select("a:has(h3)")

            # Recorremos los enlaces encontrados
            for a in enlaces_con_titulo:
                if len(urls) >= num_results:
                    break  # Cortamos si ya alcanzamos el número solicitado

                href = a.get('href')
                if href and href.startswith("http"):
                    urls.append(href)  # Guardamos la URL si es válida

        except Exception as e:
            # En caso de error (por ejemplo, timeout), mostramos el mensaje en la interfaz
            st.error(f"❌ Error al conectar con start={start}: {str(e)}")
            continue

    # ═══════════════════════════════════════════════
    # 🔗 VISUALIZACIÓN: Mostrar solo URLs en texto plano
    # ═══════════════════════════════════════════════

    if urls:
        st.subheader("🔗 Enlaces en texto plano")        # Título de sección
        st.text("\n".join(urls))                         # Mostramos todas las URLs en bloque
    else:
        st.warning("⚠️ No se encontraron enlaces estructurados.")  # En caso de no obtener nada
