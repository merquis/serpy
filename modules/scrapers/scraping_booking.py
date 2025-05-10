# modules/scrapers/scraping_booking.py

import streamlit as st
import urllib.request
import ssl
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
# 📥 Función para obtener datos de Booking
# ════════════════════════════════════════════════
def obtener_datos_booking(urls):
    resultados_json = []
    for url in urls:
        try:
            response = urllib.request.urlopen(url, timeout=30)
            html = response.read().decode('utf-8')
            soup = BeautifulSoup(html, "html.parser")

            nombre_hotel = soup.select_one('[data-testid="title"]') or soup.select_one('h2.pp-header__title')
            nombre_final = nombre_hotel.text.strip() if nombre_hotel else None

            resultados_json.append({
                "url": url,
                "nombre_hotel": nombre_final
            })
        except Exception as e:
            st.error(f"❌ Error inesperado procesando {url}: {e}")
    return resultados_json

# ════════════════════════════════════════════════
# 🎛️ Interfaz principal Streamlit
# ════════════════════════════════════════════════
def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping de nombres de hoteles en Booking (modo urllib.request)")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    # Entrada de URLs
    col1, _ = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear nombre hotel")

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Scrapeando nombres de hoteles..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)

        nombre_archivo = "datos_hoteles_booking.json"
        json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=json_bytes,
                file_name=nombre_archivo,
                mime="application/json"
            )

        with col2:
            # Botón primero
            subir_btn = st.button("☁️ Subir a Google Drive", key="subir_drive_booking")

            # Luego debajo mensajes si se hace clic
            if 'subido_ok' not in st.session_state:
                st.session_state['subido_ok'] = False

            if subir_btn:
                with st.spinner("☁️ Subiendo JSON a Google Drive (cuenta de servicio)..."):
                    if st.session_state.get("proyecto_id"):
                        carpeta_principal = st.session_state["proyecto_id"]
                        subcarpeta_id = obtener_o_crear_subcarpeta("scraper url hotel booking", carpeta_principal)

                        if subcarpeta_id:
                            enlace = subir_json_a_drive(nombre_archivo, json_bytes, subcarpeta_id)
                            if enlace:
                                st.session_state['subido_ok'] = enlace
                            else:
                                st.error("❌ Error al subir el archivo a la subcarpeta.")
                        else:
                            st.error("❌ No se pudo encontrar o crear la subcarpeta.")
                    else:
                        st.error("❌ No hay proyecto seleccionado en session_state['proyecto_id'].")

            # Mostrar mensaje de éxito si subido
            if st.session_state.get('subido_ok'):
                st.success(f"📁✅ Subido correctamente: [Ver archivo]({st.session_state['subido_ok']})")
