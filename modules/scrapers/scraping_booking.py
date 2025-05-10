# modules/scrapers/scraping_booking.py

import streamlit as st
# Importamos Playwright en lugar de urllib.request
from playwright.sync_api import sync_playwright # Usamos la versión síncrona para Streamlit
# No necesitamos ssl ni urllib.error directamente para la petición con Playwright
from bs4 import BeautifulSoup # BeautifulSoup todavía nos puede ayudar a parsear el HTML obtenido por Playwright
import json
# Asegúrate de que estos módulos existan y funcionen correctamente
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ══════════════════════════════════════════════════
# ⚙️ Configuración de la página de Streamlit
# Esta debe ser la PRIMERA llamada a Streamlit en el script principal
# ══════════════════════════════════════════════════
st.set_page_config(page_title="Scraper Booking (Playwright)", layout="wide")

# ══════════════════════════════════════════════════
# 📡 Configuración del proxy Bright Data
# ═══════════════════════════════════════════════
# Es fundamental que estas credenciales y la URL del proxy sean correctas y estén activas
proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-scraping_hoteles-country-es:9kr59typny7y@brd.superproxy.io:33335'

# La configuración del proxy en Playwright se hace al lanzar el navegador o crear el contexto
# No necesitamos configurar un abridor global como con urllib.request

# ══════════════════════════════════════════════════
# 📅 Funciones de Scraping (Usando Playwright)
# ══════════════════════════════════════════════════

def obtener_datos_booking(urls):
    """
    Extrae datos (nombre, valoración, dirección, precio) de URLs de hotel de Booking.com
    usando Playwright para manejar JavaScript.

    Args:
        urls (list): Lista de URLs de páginas de hotel de Booking.com.

    Returns:
        list: Lista de diccionarios con los datos extraídos para cada URL.
    """
    resultados = []

    # Usamos sync_playwright para un uso síncrono dentro de la función de Streamlit
    with sync_playwright() as p:
        # Lanzamos un navegador (Chromium es común)
        # headless=True para que no se abra una ventana visual (ideal para servidores)
        # Configuramos el proxy aquí
        try:
            browser = p.chromium.launch(
                headless=True,
                proxy={
                    "server": proxy_url,
                    # Playwright maneja la autenticación básica directamente en la URL del servidor
                }
            )
            st.success("✅ Navegador Playwright lanzado con proxy.")
        except Exception as e:
            st.error(f"❌ Error al lanzar Playwright con proxy: {e}")
            st.info("Intentando lanzar Playwright sin proxy. El scraping podría fallar.")
            try:
                browser = p.chromium.launch(headless=True)
                st.warning("⚠️ Playwright lanzado sin proxy.")
            except Exception as e_no_proxy:
                 st.error(f"❌ Error al lanzar Playwright sin proxy: {e_no_proxy}")
                 st.error("No se pudo lanzar Playwright. Asegúrate de tenerlo instalado (`pip install playwright` y `playwright install`).")
                 return resultados # Salir si no se puede lanzar el navegador


        # Creamos una nueva página (tab) en el navegador
        page = browser.new_page()

        # Opcional: Configurar un User-Agent si es necesario (Playwright usa uno por defecto)
        # page.set_extra_http_headers({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})


        for url in urls:
            st.info(f"🌐 Navegando a: {url} con Playwright...")
            try:
                # Navegar a la URL y esperar a que la red esté inactiva
                # Esto espera a que no haya actividad de red por un tiempo,
                # lo que suele indicar que el JavaScript terminó de cargar.
                page.goto(url, wait_until="networkidle", timeout=60000) # Aumentar timeout si es necesario (en ms)
                st.success(f"✅ Página cargada: {url}")

                # Ahora que la página está completamente cargada (incluyendo contenido JS),
                # usamos los selectores para encontrar los elementos.
                # Usamos page.locator() que es más robusto en Playwright.

                # --- Extraer Datos usando selectores CSS ---
                # Selectores basados en data-testid (suelen ser más estables) y fallbacks

                # Nombre del Hotel
                # Busca primero por data-testid="title", si no, por h2.pp-header__title
                # .first para obtener el primer elemento si hay múltiples coincidencias
                nombre_hotel_element = page.locator('[data-testid="title"], h2.pp-header__title').first
                # .text_content() es similar a .text en BeautifulSoup pero para Playwright
                nombre_hotel = nombre_hotel_element.text_content().strip() if nombre_hotel_element.count() > 0 else None


                # Valoración Total
                # Buscamos el contenedor de la valoración.
                # Luego, dentro de ese contenedor, buscamos el elemento específico que tiene la puntuación numérica.
                # Deberás inspeccionar la página (F12) para confirmar el selector exacto del número dentro de [data-testid="review-score"]
                # El selector .ac4a7896c7 es un ejemplo basado en estructuras vistas anteriormente, puede cambiar.
                valoracion_container = page.locator('[data-testid="review-score"]').first
                valoracion = None
                if valoracion_container.count() > 0:
                    # Intentamos encontrar el elemento con la puntuación numérica dentro del contenedor
                    valoracion_score_element = valoracion_container.locator('.ac4a7896c7').first # Selector probable para el número
                    if valoracion_score_element.count() == 0:
                        # Si el selector específico no funciona, intentamos obtener el texto completo del contenedor
                        valoracion = valoracion_container.text_content().strip()
                    else:
                         valoracion = valoracion_score_element.text_content().strip()


                # Dirección
                # Busca primero por data-testid="address", si no, por span.hp_address_subtitle
                direccion_element = page.locator('[data-testid="address"], span.hp_address_subtitle').first
                direccion = direccion_element.text_content().strip() if direccion_element.count() > 0 else None

                # Precio Visible (para las fechas seleccionadas)
                # Este es el más propenso a ser dinámico y variar.
                # Buscamos el contenedor principal del precio visible para las fechas.
                # Luego, dentro de ese contenedor, buscamos el elemento específico que tiene el valor numérico del precio.
                # Deberás inspeccionar la página (F12) para confirmar el selector exacto del precio.
                precio_container = page.locator('[data-testid="price-and-discounted-price"], .prco-main-price').first
                precio_minimo = None
                if precio_container.count() > 0:
                    # Intentamos encontrar el elemento con el valor del precio dentro del contenedor
                    # El selector .bui-price-display__value es un ejemplo común.
                    precio_value_element = precio_container.locator('.bui-price-display__value').first
                    if precio_value_element.count() > 0:
                        precio_minimo = precio_value_element.text_content().strip()
                    else:
                         # Si el selector específico no funciona, intentamos obtener el texto completo del contenedor
                         precio_minimo = precio_container.text_content().strip()


                # Número de Opiniones (Selector adicional)
                # Busca el elemento que contiene el número total de opiniones.
                # A menudo está cerca de la valoración o en un bloque de opiniones.
                # Deberás inspeccionar la página para encontrar el selector exacto.
                # Ejemplo de selector basado en patrones comunes:
                numero_opiniones_element = page.locator('.d8eab2cf7f.c90c0a70d3.db6369f3c6').first # Este selector es un ejemplo, ¡inspecciona la página!
                if numero_opiniones_element.count() == 0:
                     numero_opiniones_element = page.locator('.abf093bdfe.fa05109f31').first # Otro ejemplo

                numero_opiniones = numero_opiniones_element.text_content().strip() if numero_opiniones_element.count() > 0 else None
                # Podrías necesitar procesar el texto para extraer solo el número si incluye "X opiniones"


                # Añadir los resultados a la lista
                resultados.append({
                    "nombre_hotel": nombre_hotel,
                    # Estos campos están hardcodeados en tu código original.
                    # Si varían en la URL, deberías extraerlos de la URL o manejarlos de otra forma.
                    "aid": "linkafiliado",
                    "checkin": "2025-05-15",
                    "checkout": "2025-05-16",
                    "group_adults": "2",
                    "group_children": "0",
                    "no_rooms": "1",
                    "dest_id": "-369166",
                    "dest_type": "city",
                    # --- Datos extraídos con Playwright ---
                    "valoracion": valoracion,
                    "numero_opiniones": numero_opiniones,
                    "direccion": direccion,
                    "precio_minimo": precio_minimo,
                    "url": url
                })
                st.success(f"✅ Datos extraídos con Playwright para: {url}")

            except Exception as e:
                st.error(f"❌ Error procesando {url} con Playwright: {e}")
                # Opcional: Imprimir el HTML renderizado por Playwright para depuración
                # try:
                #     st.text(f"Contenido de la página (primeros 1000 chars) al momento del error:\n{page.content()[:1000]}...")
                # except Exception as content_e:
                #     st.warning(f"No se pudo obtener el contenido de la página para depuración: {content_e}")

                resultados.append({"url": url, "error": f"Error de procesamiento con Playwright: {e}"})

        # Cerramos el navegador al finalizar el bucle
        browser.close()

    return resultados

# Nota: Las funciones subir_resultado_a_drive y obtener_o_crear_subcarpeta
# no están incluidas aquí ya que dependen de tu implementación específica de Google Drive.
# Asegúrate de que estén correctamente definidas en modules.utils.drive_utils

# def subir_resultado_a_drive(nombre_archivo, contenido_bytes):
#     # ... tu implementación ...
#     pass

# def obtener_o_crear_subcarpeta(nombre_subcarpeta, parent_folder_id):
#     # ... tu implementación ...
#     pass


def render_scraping_booking():
    """
    Renderiza la interfaz de usuario de Streamlit para el scraper de Booking.com.
    """
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping de datos de hoteles en Booking (modo Playwright)")
    st.info("ℹ️ Este scraper usa Playwright para manejar contenido cargado con JavaScript.")

    # Inicializar estados de sesión si no existen
    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?aid=linkafiliado&checkin=2025-05-15&checkout=2025-05-16&group_adults=2&group_children=0&no_rooms=1&dest_id=-369166&dest_type=city"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    # Área de texto para URLs
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    # Botones de acción
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear Datos Hotel", key="buscar_datos_hotel")

    # Mostrar botones de exportar/subir solo si hay resultados
    if st.session_state.resultados_json:
        nombre_archivo = "datos_hoteles_booking_playwright.json" # Nombre de archivo diferente para distinguir
        contenido_json = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")

        with col2:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=contenido_json,
                file_name=nombre_archivo,
                mime="application/json",
                key="descargar_json"
            )

        # Asegúrate de que la función subir_resultado_a_drive esté disponible
        # if 'subir_json_a_drive' in globals(): # Comprueba si la función de Drive está definida/importada
        with col3:
            subir_a_drive_btn = st.button("☁️ Subir a Google Drive", key="subir_drive_booking")
            if subir_a_drive_btn:
                # Asegúrate de que las funciones de Drive estén importadas y disponibles
                try:
                    from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
                    with st.spinner("☁️ Subiendo JSON a Google Drive (cuenta de servicio)..."):
                        subir_resultado_a_drive(nombre_archivo, contenido_json)
                except ImportError:
                     st.error("❌ Las funciones de Google Drive no están disponibles. Asegúrate de que 'modules.utils.drive_utils' esté correctamente configurado.")


    # Lógica para ejecutar el scraping al presionar el botón
    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        if urls: # Asegurarse de que hay URLs después de limpiar
            with st.spinner("🔄 Scrapeando datos de hoteles con Playwright..."):
                # Llama a la función de scraping usando Playwright
                resultados = obtener_datos_booking(urls)
                st.session_state.resultados_json = resultados
            # Usar rerun para actualizar la interfaz y mostrar los resultados/botones
            st.experimental_rerun()
        else:
            st.warning("Por favor, introduce al menos una URL.")


    # Mostrar resultados en formato JSON si existen
    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)

# Ejemplo de cómo podrías llamar a render_scraping_booking si este archivo es el script principal de Streamlit
# if __name__ == "__main__":
#     render_scraping_booking()
