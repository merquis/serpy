# modules/scrapers/scraping_booking.py

import streamlit as st
import urllib.request
import ssl
import urllib.error
from bs4 import BeautifulSoup
import json
# Asegúrate de que estos módulos existan y funcionen correctamente
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ══════════════════════════════════════════════════
# 📡 Configuración del proxy Bright Data
# ══════════════════════════════════════════════════
# Es fundamental que estas credenciales y la URL del proxy sean correctas y estén activas
proxy_url = 'http://brd-customer-hl_bdec3e3e-zone-scraping_hoteles-country-es:9kr59typny7y@brd.superproxy.io:33335'

try:
    proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
    # Crear un contexto SSL no verificado (útil para evitar errores de certificado con proxies)
    ssl_context = ssl._create_unverified_context()
    # Construir el abridor con el manejador de proxy y SSL
    opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ssl_context))
    # Instalar el abridor para que urllib.request lo use por defecto
    urllib.request.install_opener(opener)
    st.success("✅ Configuración del proxy Bright Data aplicada.")
except Exception as e:
    st.error(f"❌ Error al configurar el proxy Bright Data: {e}")
    st.info("Continuando sin proxy. El scraping podría fallar.")
    # Si falla la configuración del proxy, resetear el abridor a None para usar la configuración por defecto
    urllib.request.install_opener(None)


# ══════════════════════════════════════════════════
# 📅 Funciones
# ══════════════════════════════════════════════════

def obtener_datos_booking(urls):
    """
    Extrae datos (nombre, valoración, dirección, precio) de URLs de hotel de Booking.com
    usando urllib.request y BeautifulSoup.

    Nota: Este método puede no extraer datos cargados dinámicamente por JavaScript.

    Args:
        urls (list): Lista de URLs de páginas de hotel de Booking.com.

    Returns:
        list: Lista de diccionarios con los datos extraídos para cada URL.
    """
    resultados = []
    # Definir un User-Agent para simular un navegador real
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for url in urls:
        st.info(f"🌐 Intentando scrapear: {url}")
        try:
            # Crear una solicitud con headers personalizados
            req = urllib.request.Request(url, headers=headers)
            # Abrir la URL usando el abridor instalado (con proxy si se configuró)
            response = urllib.request.urlopen(req, timeout=30)

            if response.status != 200:
                st.error(f"❌ Error HTTP {response.status} en {url}")
                continue

            # Leer y decodificar el contenido HTML
            html = response.read().decode('utf-8')
            # Parsear el HTML con BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")

            # --- Extraer Datos usando selectores CSS ---
            # Selectores basados en data-testid (suelen ser más estables) y fallbacks

            # Nombre del Hotel
            # Busca primero por data-testid="title", si no, por h2.pp-header__title
            nombre_hotel_element = soup.select_one('[data-testid="title"]') or soup.select_one('h2.pp-header__title')
            nombre_hotel = nombre_hotel_element.text.strip() if nombre_hotel_element else None

            # Valoración Total
            # Busca el contenedor de la valoración. El texto exacto de la puntuación puede estar dentro.
            # Intentamos obtener el texto del contenedor principal [data-testid="review-score"]
            # o buscar un elemento específico dentro si el contenedor solo es un wrapper
            valoracion_element = soup.select_one('[data-testid="review-score"]')
            # Si el contenedor se encuentra, intentamos obtener el texto.
            # A veces la puntuación numérica está en un span o div específico dentro.
            # Si el texto directo del contenedor no es la puntuación, podrías necesitar un selector más anidado
            # Por ejemplo: soup.select_one('[data-testid="review-score"] .alguna_clase_del_numero')
            valoracion = valoracion_element.text.strip() if valoracion_element else None

            # Dirección
            # Busca primero por data-testid="address", si no, por span.hp_address_subtitle
            direccion_element = soup.select_one('[data-testid="address"]') or soup.select_one('span.hp_address_subtitle')
            direccion = direccion_element.text.strip() if direccion_element else None

            # Precio Visible (para las fechas seleccionadas)
            # Busca el contenedor del precio. Este es muy propenso a ser cargado por JS.
            # Intentamos obtener el texto del contenedor principal [data-testid="price-and-discounted-price"]
            # o buscar el span que contiene el valor si está estructurado así.
            precio_minimo_element = soup.select_one('[data-testid="price-and-discounted-price"]')
            if not precio_minimo_element:
                 precio_minimo_element = soup.select_one('.prco-main-price') # Otro contenedor común

            # Si el contenedor se encuentra, intenta obtener el texto.
            # A menudo, el valor del precio está en un span con una clase como bui-price-display__value dentro de este contenedor.
            # Puedes refinar esto si obtienes texto extra:
            # precio_value_element = precio_minimo_element.select_one('.bui-price-display__value') if precio_minimo_element else None
            # precio_minimo = precio_value_element.text.strip() if precio_value_element else None
            precio_minimo = precio_minimo_element.text.strip() if precio_minimo_element else None


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
                # --- Datos extraídos ---
                "valoracion": valoracion,
                "numero_opiniones": None, # Selector para esto no implementado aún
                "direccion": direccion,
                "precio_minimo": precio_minimo, # Renombrado para claridad
                "url": url
            })
            st.success(f"✅ Datos básicos extraídos para: {url}")

        except urllib.error.URLError as e:
            st.error(f"❌ Error de conexión en {url}: {e}")
            resultados.append({"url": url, "error": f"Error de conexión: {e}"})
        except Exception as e:
            st.error(f"❌ Error inesperado procesando {url}: {e}")
            # Opcional: Imprimir el HTML para depuración si ocurre un error de parsing
            # print(f"HTML de {url} al momento del error:\n{html[:1000]}...") # Imprime los primeros 1000 caracteres
            resultados.append({"url": url, "error": f"Error de procesamiento: {e}"})

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
    st.title("🏨 Scraping de datos de hoteles en Booking (modo urllib.request)")
    st.warning("⚠️ **Nota:** Este scraper usa `urllib.request` y `BeautifulSoup`, que solo procesan el HTML inicial. Datos como valoración, dirección y precio a menudo se cargan con JavaScript y podrían no ser extraídos.")

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
        # Se cambió el texto del botón para reflejar que intenta extraer más que solo el nombre
        buscar_btn = st.button("🔍 Scrapear Datos Hotel", key="buscar_datos_hotel")

    # Mostrar botones de exportar/subir solo si hay resultados
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
            with st.spinner("🔄 Scrapeando datos de hoteles..."):
                # Llama a la función de scraping
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
