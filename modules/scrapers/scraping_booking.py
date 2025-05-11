# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import datetime
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

        # Inicializar variables
        data_extraida = {}
        imagen_destacada = None
        imagenes_secundarias = []
        descripcion = None
        servicios = []

        # Extraer JSON-LD (application/ld+json)
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            try:
                data_json = json.loads(script.string)
                if data_json.get("@type") == "Hotel":
                    data_extraida = data_json
                    break
            except Exception:
                continue

        # Extraer campos del JSON-LD
        nombre_hotel = data_extraida.get("name")
        tipo_establecimiento = data_extraida.get("@type")
        valoracion = data_extraida.get("aggregateRating", {}).get("ratingValue")
        numero_opiniones = data_extraida.get("aggregateRating", {}).get("reviewCount")
        direccion = data_extraida.get("address", {}).get("streetAddress")
        provincia = data_extraida.get("address", {}).get("addressRegion")
        pais = data_extraida.get("address", {}).get("addressCountry")
        descripcion = data_extraida.get("description")
        imagen_destacada = data_extraida.get("image")
        precio_minimo = data_extraida.get("priceRange")
        link_mapa = data_extraida.get("hasMap")

        # Mejorar calidad imagen destacada
        if imagen_destacada:
            imagen_destacada = imagen_destacada.replace("/max500/", "/max1024x768/") \
                                               .replace("/max650/", "/max1024x768/") \
                                               .replace("/max720/", "/max1024x768/")

        # Fallback imagen destacada alternativa
        if not imagen_destacada:
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                imagen_destacada = og_image['content']
                imagen_destacada = imagen_destacada.replace("/max500/", "/max1024x768/") \
                                                   .replace("/max650/", "/max1024x768/") \
                                                   .replace("/max720/", "/max1024x768/")

        # Extraer imágenes secundarias (máximo 10) mejoradas
        galeria = soup.find_all('img')
        for img in galeria:
            if img.get('src') and 'cf.bstatic.com' in img['src']:
                url_img = img['src']
                url_img = url_img.replace("/max500/", "/max1024x768/") \
                                 .replace("/max650/", "/max1024x768/") \
                                 .replace("/max720/", "/max1024x768/")
                imagenes_secundarias.append(url_img)

        imagenes_secundarias = list(dict.fromkeys(imagenes_secundarias))  # quitar duplicados
        imagenes_secundarias = imagenes_secundarias[:10]  # máximo 10 imágenes

        # Extraer servicios
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

        # Mapear resultado final
        resultado = {
            "nombre_hotel": nombre_hotel,
            "tipo_establecimiento": tipo_establecimiento,
            "valoracion": valoracion,
            "numero_opiniones": numero_opiniones,
            "direccion": direccion,
            "provincia": provincia,
            "pais": pais,
            "precio_minimo": precio_minimo,
            "descripcion": descripcion,
            "imagen_destacada": imagen_destacada,
            "imagenes_secundarias": imagenes_secundarias,
            "servicios": servicios,
            "link_mapa": link_mapa,
            "url": url,
            "checkin": datetime.date.today().strftime("%Y-%m-%d"),
            "checkout": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            "aid": "linkafiliado",
            "group_adults": "2",
            "group_children": "0",
            "no_rooms": "1",
            "dest_id": "-369166",
            "dest_type": "city",
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
