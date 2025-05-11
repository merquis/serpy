import streamlit as st
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import datetime
from urllib.parse import urlparse, parse_qs
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ════════════════════════════════════════════════════
# 📅 Función de scraping Booking usando Playwright
# ════════════════════════════════════════════════════

async def obtener_datos_booking_playwright(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(3000)

        html = await page.content()
        await browser.close()

        soup = BeautifulSoup(html, "html.parser")

        # Parsear parámetros de la URL
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        group_adults = query_params.get('group_adults', ['2'])[0]
        group_children = query_params.get('group_children', ['0'])[0]
        no_rooms = query_params.get('no_rooms', ['1'])[0]
        dest_type = query_params.get('dest_type', ['city'])[0]

        # Inicializar variables
        data_extraida = {}
        imagenes_secundarias = set()
        servicios = []

        # Extraer JSON-LD (application/ld+json)
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            try:
                data_json = json.loads(script.string)
                if isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                    data_extraida = data_json
                    break
            except Exception:
                continue

        # 📷 Extraer imágenes desde JSON interno, solo large_url
        scripts_json = soup.find_all('script', type='application/json')
        for script in scripts_json:
            if script.string and 'large_url' in script.string:
                try:
                    data_json = json.loads(script.string)
                    for key, value in data_json.items():
                        if isinstance(value, list):
                            for item in value:
                                if isinstance(item, dict) and 'large_url' in item:
                                    url_img = item['large_url']
                                    if url_img and url_img.startswith("https://cf.bstatic.com/xdata/images/hotel/max1024x768/"):
                                        imagenes_secundarias.add(url_img)
                except Exception:
                    continue

        imagenes_secundarias = list(imagenes_secundarias)[:10]

        # Sacar datos principales
        nombre_alojamiento = data_extraida.get("name") or None
        direccion = data_extraida.get("address", {}).get("streetAddress") or None
        tipo_alojamiento = data_extraida.get("@type", "Hotel") or None
        descripcion_corta = data_extraida.get("description") or None
        valoracion_global = data_extraida.get("aggregateRating", {}).get("ratingValue") or None

        # Servicios
        servicios_encontrados = soup.find_all('div', class_="bui-list__description")
        for servicio in servicios_encontrados:
            texto = servicio.get_text(strip=True)
            if texto:
                servicios.append(texto)

        if not servicios:
            servicios_encontrados = soup.find_all('li', class_="hp_desc_important_facilities")
            for servicio in servicios_encontrados:
                texto = servicio.get_text(strip=True)
                if texto:
                    servicios.append(texto)

        # Título H1
        titulo_h1_tag = soup.find("h1")
        titulo_h1 = titulo_h1_tag.get_text(strip=True) if titulo_h1_tag else None

        # Bloques de contenido H2
        bloques_h2 = []
        h2_tags = soup.find_all("h2")
        for h2 in h2_tags:
            texto = h2.get_text(strip=True)
            if texto:
                bloques_h2.append(texto)

        # Mapear resultado final respetando el orden "lista"
        resultado = {
            "checkin": datetime.date.today().strftime("%Y-%m-%d"),
            "checkout": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "group_adults": group_adults,
            "group_children": group_children,
            "no_rooms": no_rooms,
            "dest_type": dest_type,
            "nombre_alojamiento": nombre_alojamiento,
            "direccion": direccion,
            "tipo_alojamiento": tipo_alojamiento,
            "slogan_principal": None,
            "descripcion_corta": descripcion_corta,
            "estrellas": None,
            "precio_noche": None,
            "alojamiento_destacado": None,
            "isla_relacionada": None,
            "frases_destacadas": [],
            "servicios": servicios,
            "valoracion_limpieza": None,
            "valoracion_confort": None,
            "valoracion_ubicacion": None,
            "valoracion_instalaciones_servicios_": None,
            "valoracion_personal": None,
            "valoracion_calidad_precio": None,
            "valoracion_wifi": None,
            "valoracion_global": valoracion_global,
            "imagenes": imagenes_secundarias,
            "enlace_afiliado": url,
            "sitio_web_oficial": None,
            "titulo_h1": titulo_h1,
            "bloques_contenido_h2": bloques_h2,
        }

        return resultado, html

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
# 🎯 Interfaz de usuario Streamlit
# ════════════════════════════════════════════════════

def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles", key="buscar_hoteles_booking")

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
            resultados = []
            for url in urls:
                resultado, html_content = obtener_datos_booking(url)
                resultados.append(resultado)
                st.session_state.html_content = html_content
            st.session_state.resultados_json = resultados
        st.experimental_rerun()

    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)

    if "html_content" in st.session_state and st.session_state.html_content:
        st.subheader("📄 HTML capturado")
        st.download_button(
            label="⬇️ Descargar HTML capturado",
            data=st.session_state.html_content.encode("utf-8"),
            file_name="pagina_booking.html",
            mime="text/html",
            key="descargar_html"
        )
