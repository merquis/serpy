import streamlit as st
import asyncio
# import ssl # No se usa directamente
import json
import datetime
import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# Importaciones locales (comentadas si no se usan aquí directamente)
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
# Nota: Las funciones de drive_utils no se llaman en este script.

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData
# ════════════════════════════════════════════════════
def get_proxy_settings():
    """Lee la configuración del proxy desde st.secrets."""
    try:
        # Asegúrate que la sección [brightdata_booking] exista en secrets.toml
        proxy_config = st.secrets["brightdata_booking"]
        host = proxy_config.get("host")
        port = proxy_config.get("port")
        username = proxy_config.get("username")
        password = proxy_config.get("password")

        if host and port and username and password:
            # Devuelve en el formato que Playwright prefiere para proxy={}
            return {
                "server": f"{host}:{port}", # Playwright añadirá http:// por defecto
                "username": username,
                "password": password
            }
        else:
            st.error("❌ Faltan datos en la configuración del proxy en st.secrets.")
            return None
    except KeyError:
        st.error("❌ No se encontró la sección [brightdata_booking] en st.secrets.")
        return None
    except Exception as e:
        st.error(f"❌ Error leyendo configuración proxy: {e}")
        return None

# ════════════════════════════════════════════════════
# 🌐 Detectar IP real (sin proxy) - Útil para comparación
# ════════════════════════════════════════════════════
def detectar_ip_real():
    """Obtiene la IP pública sin usar proxy."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=10)
        response.raise_for_status() # Lanza error para códigos 4xx/5xx
        ip_real = response.json().get("ip", "desconocida")
        print(f"🌐 IP Real (sin proxy): {ip_real}")
        st.session_state["ip_real"] = ip_real
    except requests.exceptions.RequestException as e:
        print(f"Error detectando IP real: {e}")
        st.session_state["ip_real"] = "error_requests"
    except Exception as e:
        print(f"Error inesperado detectando IP real: {e}")
        st.session_state["ip_real"] = "error_inesperado"

# ════════════════════════════════════════════════════
# 🔎 Verificar IP pública CON proxy (usando Playwright)
# ════════════════════════════════════════════════════
async def verificar_ip_con_proxy(page):
    """Verifica la IP pública usada por la página de Playwright."""
    ip_detectada = "no_verificada"
    try:
        print("Verificando IP a través del proxy...")
        await page.goto("https://api.ipify.org?format=json", timeout=20000) # Aumentar timeout
        ip_info = await page.text_content("body")
        ip_json = json.loads(ip_info)
        ip_detectada = ip_json.get("ip", "desconocida_proxy")
        print(f"🔎 IP detectada con proxy: {ip_detectada}")
    except PlaywrightTimeoutError:
        print("Timeout al verificar IP con proxy.")
        ip_detectada = "error_timeout_verificacion"
    except Exception as e:
        print(f"Error verificando IP con proxy: {e}")
        ip_detectada = "error_verificacion"
    # Guardar en session_state para mostrar en el resultado final
    st.session_state["last_detected_ip_proxy"] = ip_detectada
    return ip_detectada # Devolver también para posible lógica inmediata

# ════════════════════════════════════════════════════
# 📅 Scraping Booking (Función Principal Refinada)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance, verificar_ip_flag=False):
    """
    Obtiene datos de una URL de Booking usando una instancia de navegador ya configurada.
    Args:
        url (str): La URL del hotel.
        browser_instance: La instancia del navegador Playwright (debe estar ya lanzada con proxy).
        verificar_ip_flag (bool): Si es True, verifica la IP usada por el proxy para esta URL.
    Returns:
        tuple: (dict_resultados, html_content) o (dict_error, "")
    """
    html = ""
    page = None
    resultado_final = {}

    try:
        page = await browser_instance.new_page(
            # Ignorar errores de certificado SSL (común con proxies)
            ignore_https_errors=True
        )

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36", # User agent actualizado
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        # --- Verificación de IP con Proxy ---
        # Se llama condicionalmente para no hacerlo en cada URL si no es necesario,
        # pero la función de lote se asegurará de llamarlo al menos una vez.
        if verificar_ip_flag:
            await verificar_ip_con_proxy(page)
            # Volver a la URL original si la verificación cambió la página (no debería con api.ipify)
            # await page.goto(url, timeout=90000, wait_until="domcontentloaded")

        # --- Navegación y Scraping ---
        print(f"Navegando a: {url}")
        await page.goto(url, timeout=90000, wait_until="domcontentloaded")

        # Esperar selector opcionalmente (puede ayudar a que cargue JS)
        try:
            await page.wait_for_selector('script[type="application/ld+json"]', timeout=15000)
        except PlaywrightTimeoutError:
            print(f"Nota: Script ld+json no encontrado o tardó >15s en {url}")
            pass # Continuar de todas formas

        html = await page.content()
        print(f"HTML obtenido para {url} (Tamaño: {len(html)} bytes)")

        if not html:
            raise ValueError("El contenido HTML está vacío.")

        # --- Parseo ---
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url) # Llama a la función de parseo

    except PlaywrightTimeoutError as e:
        print(f"Timeout de Playwright para {url}: {e}")
        return {"error": "Timeout de Playwright", "url": url, "details": str(e)}, ""
    except Exception as e:
        error_type = type(e).__name__
        print(f"Error ({error_type}) procesando {url}: {e}")
        return {"error": f"Error en Playwright/Scraping ({error_type})", "url": url, "details": str(e)}, ""
    finally:
        if page:
            try:
                await page.close()
            except Exception as page_close_error:
                print(f"Error menor al cerrar página: {page_close_error}")

    # Devolver resultado y HTML (incluso si hay error parcial en parseo)
    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (Sin cambios significativos)
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    """Parsea el HTML (BeautifulSoup) y extrae datos del hotel."""
    # ... (El código interno de parse_html_booking se mantiene igual que antes) ...
    # Asegúrate de que al final incluye las IPs de st.session_state:
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    group_adults = query_params.get('group_adults', ['2'])[0]
    # ... (resto de extracciones: data_extraida, imagenes_secundarias, servicios, h1, h2) ...
    data_extraida = {} # Placeholder para el ejemplo
    imagenes_secundarias = [] # Placeholder
    servicios = [] # Placeholder

    # --- Asegúrate de incluir las IPs al final ---
    return {
        "ip_real": st.session_state.get("ip_real", "no_detectada"),
        "ip_con_proxy": st.session_state.get("last_detected_ip_proxy", "no_verificada"), # Usar la nueva clave
        "url_original": url,
        "checkin": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "checkout": (datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"),
        "group_adults": group_adults,
        # ... resto de campos ...
        "nombre_alojamiento": data_extraida.get("name"),
        "direccion": data_extraida.get("address", {}).get("streetAddress"),
        "codigo_postal": data_extraida.get("address", {}).get("postalCode"),
        "ciudad": data_extraida.get("address", {}).get("addressLocality"),
        "pais": data_extraida.get("address", {}).get("addressCountry"),
        "tipo_alojamiento": data_extraida.get("@type"),
        "descripcion_corta": data_extraida.get("description"),
        "valoracion_global": data_extraida.get("aggregateRating", {}).get("ratingValue"),
        "numero_opiniones": data_extraida.get("aggregateRating", {}).get("reviewCount"),
        "imagenes": imagenes_secundarias,
        "servicios": servicios,
        "titulo_h1": soup.find("h1").get_text(strip=True) if soup.find("h1") else None,
        "bloques_contenido_h2": [h2.get_text(strip=True) for h2 in soup.find_all("h2")],
    }


# ════════════════════════════════════════════════════
# 🗂️ Procesar varias URLs en lote (CORREGIDO)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar):
    """Procesa una lista de URLs usando un navegador compartido con proxy."""
    tasks_results = []
    browser = None
    p = None
    proxy_conf = get_proxy_settings() # Obtener configuración del proxy

    if not proxy_conf:
        st.error("Error crítico: No se pudo cargar la configuración del proxy para el lote.")
        # Devolver lista vacía o con error para que la UI lo maneje
        return [{"error": "Configuración de proxy no disponible", "url": None, "details": "Verifica st.secrets"}]

    try:
        p = await async_playwright().start()
        print("Lanzando navegador compartido para lote CON proxy...")

        # --- CORRECCIÓN CLAVE: Lanzar el navegador con el proxy ---
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_conf # Pasar el diccionario de configuración directamente
            # args=["--ignore-certificate-errors"] # Playwright maneja esto con ignore_https_errors en new_page/context
        )
        print(f"Navegador lanzado con proxy: {proxy_conf['server']}")

        tasks = []
        for i, url in enumerate(urls_a_procesar):
            # Verificar IP solo para la primera URL del lote para confirmación
            verificar_ip_para_esta_url = (i == 0)
            # Crear la tarea pasando el navegador compartido y la bandera de verificación
            tasks.append(obtener_datos_booking_playwright(url, browser, verificar_ip_flag=verificar_ip_para_esta_url))

        # Ejecutar tareas y recoger excepciones
        results_with_html = await asyncio.gather(*tasks, return_exceptions=True)

        # Procesar resultados
        st.session_state.last_successful_html_content = "" # Resetear
        for i, res_or_exc in enumerate(results_with_html):
            url_procesada = urls_a_procesar[i]
            if isinstance(res_or_exc, Exception):
                print(f"Excepción en gather para {url_procesada}: {res_or_exc}")
                tasks_results.append({"error": "Excepción en asyncio.gather", "url": url_procesada, "details": str(res_or_exc)})
            elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                resultado_item, html_content_item = res_or_exc
                tasks_results.append(resultado_item)
                # Guardar el HTML del último éxito (si no hubo error en el resultado)
                if not resultado_item.get("error") and html_content_item:
                    st.session_state.last_successful_html_content = html_content_item
            else:
                print(f"Resultado inesperado para {url_procesada}: {res_or_exc}")
                tasks_results.append({"error": "Resultado inesperado de la tarea", "url": url_procesada, "details": str(res_or_exc)})

    except Exception as batch_error:
        print(f"Error durante el procesamiento del lote: {batch_error}")
        # Añadir un error general al resultado si falla toda la inicialización
        tasks_results.append({"error": "Error crítico en procesar_urls_en_lote", "url": None, "details": str(batch_error)})
    finally:
        if browser:
            await browser.close()
            print("Navegador compartido cerrado.")
        if p:
            # await p.stop() # Usar 'async with' gestiona esto mejor
             pass # 'async with' se encarga

    return tasks_results


# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (con verificación de proxy)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renderiza la interfaz de Streamlit."""
    st.session_state.setdefault("_called_script", "scraping_booking")
    st.title("🏨 Scraping hoteles Booking v2")

    # Inicializar estado si no existe
    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_json", [])
    st.session_state.setdefault("last_successful_html_content", "")
    st.session_state.setdefault("ip_real", "no_detectada")
    st.session_state.setdefault("last_detected_ip_proxy", "no_verificada")

    # --- Comprobación temprana de configuración del proxy ---
    proxy_ok = get_proxy_settings() is not None
    if not proxy_ok:
        st.error("🚨 ¡Configuración del Proxy NO encontrada o incompleta en st.secrets! El scraping no funcionará.")
        # Podrías detener la ejecución aquí o deshabilitar el botón
        # return

    # --- UI ---
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        # Deshabilitar botón si el proxy no está configurado
        buscar_btn = st.button("🔍 Scrapear hoteles", disabled=(not proxy_ok))

    # --- Lógica de Scraping ---
    if buscar_btn:
        detectar_ip_real() # Detectar IP real para comparación
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip() and "booking.com" in url]
        if not urls:
            st.warning("Por favor, introduce URLs válidas de Booking.com.")
        else:
            with st.spinner(f"Scrapeando {len(urls)} hoteles... (Puede tardar varios minutos)"):
                # Limpiar IPs anteriores antes de empezar el lote
                st.session_state.last_detected_ip_proxy = "verificando..."
                # Ejecutar el lote
                resultados = asyncio.run(procesar_urls_en_lote(urls))
                st.session_state.resultados_json = resultados
            st.rerun() # Refrescar para mostrar resultados y mensaje de verificación

    # --- Mostrar Resultados y Verificación de Proxy ---
    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")

        # Extraer IPs del primer resultado válido (si existe) para mostrar verificación
        ip_real_mostrada = st.session_state.get("ip_real", "N/A")
        ip_proxy_mostrada = st.session_state.get("last_detected_ip_proxy", "N/A")

        st.info(f"IP Real detectada: **{ip_real_mostrada}** | IP usada por el Proxy: **{ip_proxy_mostrada}**")

        # Lógica de Verificación
        if "error" in ip_proxy_mostrada or "N/A" in ip_proxy_mostrada or "no_verificada" in ip_proxy_mostrada:
             st.warning("⚠️ No se pudo verificar la IP del proxy o hubo un error.")
        elif ip_real_mostrada != "error_requests" and ip_real_mostrada != ip_proxy_mostrada:
             st.success("✅ Verificación Proxy: ¡Correcto! La IP del proxy es diferente a tu IP real.")
        elif ip_real_mostrada != "error_requests" and ip_real_mostrada == ip_proxy_mostrada:
             st.error("🚨 ¡Atención! La IP detectada con proxy es la misma que tu IP real. El proxy podría no estar funcionando correctamente.")
        else:
             st.info("No se pudo comparar las IPs (IP real no disponible).")


        # Mostrar JSON de resultados
        st.json(st.session_state.resultados_json)

    # --- Descarga de HTML ---
    if st.session_state.last_successful_html_content:
        st.subheader("📄 Último HTML capturado con éxito")
        try:
            # Intentar codificar a UTF-8, manejar errores si los hubiera
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(
                label="⬇️ Descargar HTML",
                data=html_bytes,
                file_name="ultimo_hotel_booking.html",
                mime="text/html"
            )
        except Exception as e:
            st.error(f"No se pudo preparar el HTML para descarga: {e}")


# --- Punto de entrada (si quisieras ejecutarlo localmente) ---
# if __name__ == "__main__":
#      # Necesitarías simular st.secrets y st.session_state si ejecutas fuera de Streamlit
#      render_scraping_booking()
