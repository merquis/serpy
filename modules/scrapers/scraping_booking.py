import streamlit as st
import asyncio
import json
import datetime
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from modules.utils.playwright_utils import (
    PlaywrightConfig,
    obtener_html_simple,
    procesar_urls_en_lote,
    crear_config_booking
)

# ════════════════════════════════════════════════════
# 📅 Scraping Booking usando el módulo reutilizable
# ════════════════════════════════════════════════════
async def obtener_datos_booking(url: str) -> tuple:
    """
    Obtiene los datos de un hotel de Booking usando Playwright y BeautifulSoup.
    
    Args:
        url: URL del hotel en Booking.com
        
    Returns:
        Tupla con (datos_parseados, html_content)
    """
    # Usar la configuración específica de Booking
    config = crear_config_booking()
    
    # Obtener HTML usando el módulo reutilizable
    resultado, html = await obtener_html_simple(url, config)
    
    # Si hay error, retornar el error
    if resultado.get("error"):
        return resultado, ""
    
    # Si no hay HTML, retornar error
    if not html:
        return {
            "error": "HTML_Vacio",
            "url_original": url,
            "details": "No se obtuvo contenido HTML."
        }, ""
    
    # Parsear el HTML con BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    datos_parseados = parse_html_booking(soup, url)
    
    return datos_parseados, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (Imágenes corregidas)
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    group_adults = query_params.get('group_adults', [''])[0]
    group_children = query_params.get('group_children', [''])[0]
    no_rooms = query_params.get('no_rooms', [''])[0]
    checkin_year_month_day = query_params.get('checkin', [''])[0]
    checkout_year_month_day = query_params.get('checkout', [''])[0]
    dest_type = query_params.get('dest_type', [''])[0]
    data_extraida, imagenes_secundarias, servicios = {}, [], []

    try:
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string)
                    if isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                        data_extraida = data_json
                        break
                except:
                    continue
    except:
        pass

    try:
        found_urls_img = set()
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src")
            if src and src.startswith("https://cf.bstatic.com/xdata/images/hotel/") and ".jpg" in src:
                if len(imagenes_secundarias) < 15 and src not in found_urls_img:
                    if "/max1024x768/" not in src:
                        src = re.sub(r"/max[^/]+/", "/max1024x768/", src)

                    if "&o=" in src:
                        src = src.split("&o=")[0]

                    imagenes_secundarias.append(src)
                    found_urls_img.add(src)
    except Exception as e:
        print(f"Error extrayendo imágenes de <img>: {e}")

    try:
        possible_classes = ["hotel-facilities__list", "facilitiesChecklistSection", "hp_desc_important_facilities", "bui-list__description", "db29ecfbe2"]
        servicios_set = set()
        for cn in possible_classes:
            for container in soup.find_all(class_=cn):
                for item in container.find_all(['li', 'span', 'div'], recursive=True):
                    texto = item.get_text(strip=True)
                    if texto and len(texto) > 3:
                        servicios_set.add(texto)
        servicios = sorted(list(servicios_set))
    except:
        pass

    titulo_h1_tag = soup.find("h1")
    titulo_h1 = titulo_h1_tag.get_text(strip=True) if titulo_h1_tag else data_extraida.get("name", "")
    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]

    address_info = data_extraida.get("address", {})
    rating_info = data_extraida.get("aggregateRating", {})

    return {
        "url_original": url,
        "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "busqueda_checkin": checkin_year_month_day,
        "busqueda_checkout": checkout_year_month_day,
        "busqueda_adultos": group_adults,
        "busqueda_ninos": group_children,
        "busqueda_habitaciones": no_rooms,
        "busqueda_tipo_destino": dest_type,
        "nombre_alojamiento": data_extraida.get("name", titulo_h1),
        "tipo_alojamiento": data_extraida.get("@type", "Desconocido"),
        "direccion": address_info.get("streetAddress"),
        "codigo_postal": address_info.get("postalCode"),
        "ciudad": address_info.get("addressLocality"),
        "pais": address_info.get("addressCountry"),
        "url_hotel_booking": data_extraida.get("url"),
        "descripcion_corta": data_extraida.get("description"),
        "valoracion_global": rating_info.get("ratingValue"),
        "mejor_valoracion_posible": rating_info.get("bestRating", "10"),
        "numero_opiniones": rating_info.get("reviewCount"),
        "rango_precios": data_extraida.get("priceRange"),
        "titulo_h1": titulo_h1,
        "subtitulos_h2": h2s,
        "servicios_principales": servicios,
        "imagenes": imagenes_secundarias,
    }

# ════════════════════════════════════════════════════
# 🗂️ Procesar URLs de Booking en lote
# ════════════════════════════════════════════════════
async def procesar_urls_booking_lote(urls_a_procesar):
    """
    Procesa múltiples URLs de Booking en lote.
    
    Args:
        urls_a_procesar: Lista de URLs de Booking para procesar
        
    Returns:
        Lista de resultados parseados
    """
    # Usar configuración específica de Booking
    config = crear_config_booking()
    
    # Obtener HTML de todas las URLs usando el módulo reutilizable
    resultados_html = await procesar_urls_en_lote(urls_a_procesar, config)
    
    final_results = []
    
    for resultado, html in resultados_html:
        # Si hay error, añadir el error
        if resultado.get("error"):
            final_results.append(resultado)
        # Si hay HTML, parsearlo
        elif html:
            soup = BeautifulSoup(html, "html.parser")
            datos_parseados = parse_html_booking(soup, resultado["url_original"])
            final_results.append(datos_parseados)
            
            # Guardar el último HTML exitoso en session state
            if not datos_parseados.get("error"):
                st.session_state.last_successful_html_content = html
        else:
            final_results.append({
                "error": "Resultado_Inesperado",
                "url_original": resultado.get("url_original", "URL desconocida"),
                "details": "No se obtuvo HTML"
            })
    
    return final_results

# ════════════════════════════════════════════════════
# 🎯 Renderizar interfaz en Streamlit
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.title("🏨 Scraping Hoteles Booking (Playwright Básico)")

    st.session_state.setdefault("urls_input",
        "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?checkin=2025-07-10&checkout=2025-07-15&group_adults=2&group_children=0&no_rooms=1&dest_type=hotel"
    )
    st.session_state.setdefault("resultados_finales", [])
    st.session_state.setdefault("last_successful_html_content", "")

    st.session_state.urls_input = st.text_area(
        "📝 Pega URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150
    )

    if st.button("🔍 Scrapear Hoteles"):
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.startswith("https://www.booking.com/hotel/")]

        if not urls:
            st.warning("Introduce URLs válidas de Booking.com.")
            st.stop()

        with st.spinner(f"Procesando {len(urls)} URLs..."):
            resultados = asyncio.run(procesar_urls_booking_lote(urls))
        st.session_state.resultados_finales = resultados
        st.rerun()

    if st.session_state.resultados_finales:
        st.subheader("📊 Resultados")
        st.json(st.session_state.resultados_finales)

    if st.session_state.last_successful_html_content:
        st.subheader("📄 Último HTML Capturado")
        html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
        st.download_button("⬇️ Descargar HTML", data=html_bytes, file_name="hotel_booking.html", mime="text/html")

# ════════════════════════════════════════════════════
# 🚀 Ejecutar
# ════════════════════════════════════════════════════
if __name__ == "__main__":
    render_scraping_booking()
