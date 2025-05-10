# modules/scrapers/scraping_booking.py

import streamlit as st
import urllib.request
import ssl
import urllib.error
from bs4 import BeautifulSoup
import json
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ════════════════════════════════════════════════
# 📡 Configuración del proxy Bright Data
# ════════════════════════════════════════════════
proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-scraping_hoteles-country-es:9kr59typny7y@brd.superproxy.io:33335'

proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
ssl_context = ssl._create_unverified_context()
opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ssl_context))
urllib.request.install_opener(opener)

# ════════════════════════════════════════════════
# 📥 Función para obtener nombre de hoteles desde URLs de Booking
# ════════════════════════════════════════════════
def obtener_datos_booking(urls):
    resultados = []
    for url in urls:
        try:
            response = urllib.request.urlopen(url, timeout=30)
            if response.status != 200:
                st.error(f"❌ Error HTTP {response.status} en {url}")
                continue

            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, "html.parser")
           

            nombre_hotel = soup.select_one('[data-testid="title"]') or soup.select_one('h2.pp-header__title')
            resultados.append({
                "url": url,
                "nombre_hotel": nombre_hotel.text.strip() if nombre_hotel else None
            })

        except urllib.error.URLError as e:
            st.error(f"❌ Error de conexión en {url}: {e}")
        except Exception as e:
            st.error(f"❌ Error inesperado procesando {url}: {e}")

    return resultados

# ════════════════════════════════════════════════
# ☁️ Función auxiliar para subir JSON al Drive
# ════════════════════════════════════════════════
def subir_resultado_a_drive(nombre_archivo, contenido_bytes):
    proyecto_id = st.session_state.get("proyecto_id")
    if not proyecto_id:
        st.error("❌ No hay proyecto seleccionado en session_state['proyecto_id'].")
        return

    subcarpeta_id = obtener_o_crear_subcarpeta("scraper url hotel booking", proyecto_id)
    if not subcarpeta_id:
        st.error("❌ No se pudo encontrar o crear la subcarpeta.")
        return

    enlace = subir_json_a_drive(nombre_archivo, contenido_bytes, subcarpeta_id)
    if enlace:
        st.success(f"✅ Subido correctamente: [Ver archivo]({enlace})", icon="📁")
    else:
        st.error("❌ Error al subir el archivo a la subcarpeta.")

# ════════════════════════════════════════════════
# 🎛️ Interfaz principal Streamlit
# ════════════════════════════════════════════════
def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping de nombres de hoteles en Booking (modo urllib.request)")

    # Estado inicial
    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    # Área de entrada de URLs
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    # Botones principales en 3 columnas
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear nombre hotel", key="buscar_nombre_hotel")

    if st.session_state.resultados_json:
        nombre_archivo = "datos_hoteles_booking.json"
        contenido_json = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        with col2:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=contenido_json,
                file_name=nombre_archivo,
                mime="application/json",
                key="descargar_json"
            )

        with col3:
            subir_a_drive_btn = st.button("☁️ Subir a Google Drive", key="subir_drive_booking")
            if subir_a_drive_btn:
                with st.spinner("☁️ Subiendo JSON a Google Drive (cuenta de servicio)..."):
                    subir_resultado_a_drive(nombre_archivo, contenido_json)

    # Procesar scraping si se hace clic en buscar
    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Scrapeando nombres de hoteles..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados
        st.experimental_rerun()  # 🔄 Refrescar para mostrar botones de exportar/subir

    # Mostrar resultados
    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)
