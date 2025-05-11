# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import json
import datetime
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ════════════════════════════════════════════════════
# 📅 Funciones de scraping Booking usando Playwright
# ════════════════════════════════════════════════════

async def obtener_datos_booking_playwright(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)

        # Esperar para asegurar que carga todo
        await page.wait_for_timeout(3000)

        html = await page.content()

        # Buscar los scripts de tipo application/ld+json
        scripts = await page.query_selector_all('script[type="application/ld+json"]')
        data_extraida = {}

        for script in scripts:
            contenido = await script.inner_text()
            try:
                datos_json = json.loads(contenido)
                if datos_json.get("@type") == "Hotel":
                    data_extraida = datos_json
                    break
            except Exception:
                continue

        await browser.close()

        # Extraer los datos
        nombre_hotel = data_extraida.get("name")
        valoracion = data_extraida.get("aggregateRating", {}).get("ratingValue")
        direccion = data_extraida.get("address", {}).get("streetAddress")
        precio_minimo = data_extraida.get("priceRange")

        return {
            "nombre_hotel": nombre_hotel,
            "valoracion": valoracion,
            "direccion": direccion,
            "precio_minimo": precio_minimo,
            "url": url,
            "checkin": datetime.date.today().strftime("%Y-%m-%d"),
            "checkout": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "aid": "linkafiliado",
            "group_adults": "2",
            "group_children": "0",
            "no_rooms": "1",
            "dest_id": "-369166",
            "dest_type": "city",
        }, html

def obtener_datos_booking(url):
    return asyncio.run(obtener_datos_booking_playwright(url))

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

# ════════════════════════════════════════════════════
# 🎯 Interfaz de usuario
# ════════════════════════════════════════════════════

def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?aid=linkafiliado&checkin=2025-05-15&checkout=2025-05-16&group_adults=2&group_children=0&no_rooms=1&dest_id=-369166&dest_type=city"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

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

    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Scrapeando nombres de hoteles..."):
            resultados = []
            for url in urls:
                resultado, html_content = obtener_datos_booking(url)
                resultados.append(resultado)

                # ════════════════════════════════════════════════════
                # ✨ BLOQUE: Guardar HTML capturado
                st.session_state.html_content = html_content
                # ════════════════════════════════════════════════════

            st.session_state.resultados_json = resultados
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)

    # ════════════════════════════════════════════════════
    # ✨ BLOQUE EXTRA: BOTÓN DESCARGAR HTML
    if "html_content" in st.session_state and st.session_state.html_content:
        st.subheader("📄 HTML capturado")
        st.download_button(
            label="⬇️ Descargar HTML capturado",
            data=st.session_state.html_content.encode("utf-8"),
            file_name="pagina_booking.html",
            mime="text/html",
            key="descargar_html"
        )
    # ✨ FIN BLOQUE EXTRA HTML
    # ════════════════════════════════════════════════════
