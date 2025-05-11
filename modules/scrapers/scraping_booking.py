import streamlit as st
import urllib.parse
import json
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ══════════════════════════════════════════════════
# 📅 Funciones
# ══════════════════════════════════════════════════

async def scrape_booking_data(urls):
    resultados = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        for url in urls:
            try:
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(3000)  # Esperar 3s para asegurar que cargue bien

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # Buscar el bloque de datos JSON-LD
                script_tag = soup.find("script", type="application/ld+json")
                datos_json = {}

                if script_tag:
                    try:
                        datos_json = json.loads(script_tag.string)
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo parsear JSON-LD en {url}: {e}")

                nombre_hotel = datos_json.get("name")
                valoracion = datos_json.get("aggregateRating", {}).get("ratingValue")
                direccion = datos_json.get("address", {}).get("streetAddress")
                precio_minimo = datos_json.get("priceRange")

                # Guardar todo el HTML si quieres revisarlo
                st.download_button(
                    label="⬇️ Descargar HTML de prueba",
                    data=content.encode("utf-8"),
                    file_name="html_booking_prueba.html",
                    mime="text/html",
                    key=f"descargar_html_{url}"
                )

                resultados.append({
                    "nombre_hotel": nombre_hotel,
                    "valoracion": valoracion,
                    "direccion": direccion,
                    "precio_minimo": precio_minimo,
                    "url": url,
                    "checkin": st.session_state.get("checkin", "2025-05-15"),
                    "checkout": st.session_state.get("checkout", "2025-05-16"),
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

def obtener_datos_booking(urls):
    return asyncio.run(scrape_booking_data(urls))

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
        # URL de prueba con check-in/check-out actualizados automáticamente
        base_url = (
            "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
            "?aid=linkafiliado"
            "&checkin=2025-05-15"
            "&checkout=2025-05-16"
            "&group_adults=2"
            "&group_children=0"
            "&no_rooms=1"
            "&dest_id=-369166"
            "&dest_type=city"
        )
        st.session_state.urls_input = base_url

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
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)
