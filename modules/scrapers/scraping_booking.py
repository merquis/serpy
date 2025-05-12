# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
import json
import datetime
import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
# Asumiendo que estas funciones existen en tu proyecto
# from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData
# ════════════════════════════════════════════════════
def get_proxy_settings():
    try:
        brightdata = st.secrets["brightdata_booking"]
        # Asegúrate que el host incluya el protocolo si es necesario,
        # aunque Playwright generalmente lo maneja bien sin él para http.
        # Para https o socks, necesitarías especificar el protocolo en el server string.
        # proxy_server = f"http://{brightdata['host']}:{brightdata['port']}" # Original
        proxy_server = f"{brightdata['host']}:{brightdata['port']}" # Ajustado - Playwright añade http:// por defecto si no está
        username = brightdata['username']
        password = brightdata['password']
        return {
            "server": proxy_server,
            "username": username,
            "password": password
        }
    except KeyError:
        st.error("⚠️ Error: No se encontraron las credenciales de 'brightdata_booking' en st.secrets.")
        return None
    except Exception as e:
        st.error(f"⚠️ Error al cargar la configuración del proxy: {e}")
    return None

# ... (detectar_ip_real se mantiene igual) ...

# ════════════════════════════════════════════════════
# 📅 Scraping Booking usando Playwright + Proxy
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance=None, debug=False):
    html = ""
    close_browser_on_finish = False
    current_p = None
    page = None # Inicializar page a None

    try:
        proxy_config = get_proxy_settings() # Obtener config al inicio
        if not proxy_config:
             return {"error": "Configuración del proxy no disponible", "url": url}, ""

        if not browser_instance:
            close_browser_on_finish = True
            current_p = await async_playwright().start()
            print("Lanzando nuevo navegador con proxy...") # Debug print
            browser_instance = await current_p.chromium.launch(
                headless=True,
                # *** CORRECCIÓN CLAVE 1: Pasar todo el diccionario proxy aquí ***
                proxy=proxy_config
            )

        # Crear la página desde la instancia del navegador (nueva o pasada)
        page = await browser_instance.new_page()

        # *** CORRECCIÓN CLAVE 2: Eliminar page.authenticate ***
        # La autenticación ya se manejó al lanzar el navegador.
        # await page.authenticate({ # <-- LÍNEA ELIMINADA
        #     "username": proxy_config['username'], # <-- LÍNEA ELIMINADA
        #     "password": proxy_config['password']  # <-- LÍNEA ELIMINADA
        # })                                       # <-- LÍNEA ELIMINADA

        # Configurar cabeceras (esto está bien)
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        })

        # Verificar IP si debug está activado (esto está bien)
        if debug:
            try:
                print("Verificando IP con proxy...") # Debug print
                await page.goto("https://api.ipify.org?format=json", timeout=20000) # Aumentar timeout si es necesario
                ip_info = await page.text_content("body")
                ip_json = json.loads(ip_info)
                detected_ip = ip_json.get("ip", "desconocida")
                print(f"IP detectada con proxy: {detected_ip}") # Debug print
                st.session_state["last_detected_ip"] = detected_ip
            except Exception as ip_error:
                print(f"Error al verificar IP: {ip_error}")
                st.session_state["last_detected_ip"] = "error_verificando"


        print(f"Navegando a la URL: {url}") # Debug print
        await page.goto(url, timeout=90000, wait_until="domcontentloaded")

        # Esperar selector (esto está bien)
        try:
            await page.wait_for_selector('script[type="application/ld+json"]', timeout=20000)
        except PlaywrightTimeoutError:
            print("Timeout esperando script ld+json, continuando...") # Debug print
            pass # Es normal que a veces no esté o tarde, no necesariamente un error fatal

        html = await page.content()
        print("Contenido HTML obtenido.") # Debug print
        await page.close()
        page = None # Marcar como cerrada

    except PlaywrightTimeoutError as e:
        print(f"Timeout de Playwright para {url}: {e}") # Debug print
        return {"error": "Timeout de Playwright", "url": url, "details": str(e)}, ""
    except Exception as e:
        # Captura más específica del error si es posible
        error_type = type(e).__name__
        print(f"Error general ({error_type}) en Playwright para {url}: {e}") # Debug print
        # Comprobar si el error es el que vimos ("'Page' object has no attribute 'authenticate'") aunque ya no debería pasar
        return {"error": f"Error general Playwright ({error_type})", "url": url, "details": str(e)}, ""
    finally:
        # Cerrar recursos de forma segura
        if page: # Si la página aún existe (por error antes del close)
             try:
                 await page.close()
             except Exception as page_close_error:
                 print(f"Error al cerrar la página en finally: {page_close_error}")
        if close_browser_on_finish and browser_instance:
            await browser_instance.close()
            print("Navegador propio cerrado.") # Debug print
        if close_browser_on_finish and current_p:
            await current_p.stop()

    if not html:
        print(f"HTML vacío obtenido para {url}") # Debug print
        return {"error": "HTML vacío", "url": url}, ""

    # Parsear el HTML (esto se mantiene igual)
    soup = BeautifulSoup(html, "html.parser")
    resultado = parse_html_booking(soup, url)
    return resultado, html

# ... (parse_html_booking se mantiene igual) ...

# ════════════════════════════════════════════════════
# 🗂️ Procesar varias URLs en lote
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar):
    tasks_results = []
    browser = None # Inicializar browser a None
    p = None # Inicializar p a None

    proxy_config = get_proxy_settings() # Obtener config una vez
    if not proxy_config:
        st.error("Error crítico: No se pudo cargar la configuración del proxy para el lote.")
        return [{"error": "Proxy configuration missing for batch"}]

    try:
        p = await async_playwright().start()
        print("Lanzando navegador compartido para lote con proxy...") # Debug print
        browser = await p.chromium.launch(
            headless=True,
            # *** CORRECCIÓN CLAVE 3: Pasar todo el diccionario proxy aquí también ***
            proxy=proxy_config
        )

        # Crear tareas pasando la instancia del navegador compartida
        # La función obtener_datos_booking_playwright NO intentará autenticar de nuevo
        tasks = [obtener_datos_booking_playwright(u, browser, debug=True) for u in urls_a_procesar] # Activar debug para ver IPs
        tasks_results_with_html = await asyncio.gather(*tasks, return_exceptions=True)

        # Procesar resultados (esto se mantiene igual)
        for res_or_exc in tasks_results_with_html:
            if isinstance(res_or_exc, Exception):
                tasks_results.append({"error": "Excepción en asyncio.gather", "details": str(res_or_exc)})
            elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                resultado_item, _ = res_or_exc # Ignoramos el html aquí
                tasks_results.append(resultado_item)
            else:
                tasks_results.append({"error": "Resultado inesperado de la tarea", "details": str(res_or_exc)})

    except Exception as batch_error:
        print(f"Error durante el procesamiento del lote: {batch_error}")
        tasks_results.append({"error": "Error en procesar_urls_en_lote", "details": str(batch_error)})
    finally:
        # Cerrar recursos de forma segura
        if browser:
            await browser.close()
            print("Navegador compartido cerrado.") # Debug print
        if p:
            await p.stop()

    return tasks_results

# ... (render_scraping_booking se mantiene igual, pero ahora debería funcionar) ...

# --- Añadir esto al final si quieres probar el script directamente ---
# if __name__ == "__main__":
#     # Ejemplo de cómo podrías llamar a la función de lote para probar
#     async def main_test():
#         test_urls = [
#             "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html",
#             # Añade otra URL de prueba si quieres
#             # "https://www.booking.com/hotel/es/nh-collection-madrid-eurobuilding.es.html"
#         ]
#         # Simular st.secrets para prueba local si no usas Streamlit directamente
#         # Necesitarías definir st como un objeto mock o adaptar get_proxy_settings
#         # Para una prueba rápida, podrías hardcodear temporalmente la config
#         # o leerla de un .env localmente.
#         # Aquí asumimos que st.secrets funciona o está mockeado.
#         # También simular st.session_state si es necesario para las IPs
#         class MockSessionState:
#             def __init__(self):
#                 self._state = {}
#             def __setitem__(self, key, value):
#                 self._state[key] = value
#             def get(self, key, default=None):
#                 return self._state.get(key, default)
#
#         st.session_state = MockSessionState()
#         st.secrets = { # Simulación de secrets
#              "brightdata_booking": {
#                 "host": "brd.superproxy.io",
#                 "port": "22225", # Puerto de ejemplo, usa el tuyo
#                 "username": "brd-customer-hl_xxxxxx-zone-scraping_hoteles-country-es", # Usa tu user real
#                 "password": "TU_PASSWORD_REAL" # Usa tu pass real
#              }
#         }
#
#         print("Iniciando prueba de scraping en lote...")
#         resultados = await procesar_urls_en_lote(test_urls)
#         print("\nResultados del scraping:")
#         print(json.dumps(resultados, indent=2, ensure_ascii=False))
#
#     asyncio.run(main_test())
