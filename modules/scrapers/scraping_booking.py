# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import json
import datetime
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ══════════════════════════════════════════════════
# 📅 Funciones auxiliares
# ══════════════════════════════════════════════════

async def obtener_datos_booking_playwright(urls):
    resultados = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        for url in urls:
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_load_state('networkidle')
                html = await page.content()

                # Guardar el HTML en un archivo para inspeccionarlo
                nombre_archivo_html = "pagina_booking.html"
                with open(nombre_archivo_html, "w", encoding="utf-8") as f:
                    f.write(html)

                # Extraer datos usando selectores
                nombre_hotel_elem = await page.query_selector('[data-testid="title"], h2.pp-header__title')
                valoracion_elem = await page.query_selector('[data-testid="review-score"]')
                direccion_elem = await page.query_selector('[data-testid="address"], span.hp_address_subtitle')
                precio_minimo_elem = await page.query_selector('[data-testid="price-and-discounted-price"]')

                resultados.append({
                    "nombre_hotel": await nombre_hotel_elem.inner_text() if nombre_hotel_elem else None,
                    "valoracion": await valoracion_elem.inner_text() if valoracion_elem else None,
                    "direccion": await direccion_elem.inner_text() if direccion_elem else None,
                    "precio_minimo": await precio_minimo_elem.inner_text() if precio_minimo_elem else None,
                    "url": url,
                    "checkin": datetime.date.today().isoformat(),
                    "checkout": (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
                    "aid": "linkafiliado",
                    "group_adults": "2",
                    "group_children": "0",
                    "no_rooms": "1",
                    "dest_id": "-369166",
                    "dest_type": "city",
                })

            except Exception as e:
                st.error(f"❌ Error procesando {url}: {e}")

        await browser.close()

    return resultados


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


def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    if "urls_input" not in st.session_state:
        hoy = datetime.date.today().isoformat()
        manana = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        st.session_state.urls_input = f"https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?aid=linkafiliado&checkin={hoy}&checkout={manana}&group_adults=2&group_children=0&no_rooms=1&dest_id=-369166&dest_type=city"

    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles", key="buscar_nombre_hotel")

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
        with st.spinner("🔄 Scrapeando hoteles..."):
            st.session_state.resultados_json = asyncio.run(obtener_datos_booking_playwright(urls))
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)
