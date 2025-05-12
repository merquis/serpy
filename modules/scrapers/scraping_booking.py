# modules/scrapers/scraping_booking.py

import streamlit as st
import asyncio
import json
import datetime
import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
# Make sure these utility functions exist and work as expected
from modules.utils.drive_utils import subir_json_a_drive, obtener_o_crear_subcarpeta
import traceback # For detailed error logging

# ════════════════════════════════════════════════════
# 🛠️ Configuración del Proxy BrightData
# ════════════════════════════════════════════════════
def get_proxy_settings():
    """Retrieves proxy settings from Streamlit secrets."""
    try:
        # Ensure these keys exactly match your secrets.toml file structure
        proxy_server = st.secrets["brightdata_booking"]["proxy"]
        if proxy_server and isinstance(proxy_server, str) and proxy_server.startswith("http"):
            # This format { "server": "http://user:pass@host:port" } is correct for Playwright
            # Avoid logging the full proxy string containing credentials
            print(f"🔑 Proxy settings loaded successfully (starts with: {proxy_server[:30]}...).")
            return {"server": proxy_server}
        elif not proxy_server:
             st.warning("⚠️ Proxy string found in secrets but is empty.")
             print("❌ Proxy string found in secrets but is empty.")
             return None
        else:
            st.error(f"❌ Invalid proxy string format found in secrets: {type(proxy_server)}")
            print(f"❌ Invalid proxy string format found in secrets: {type(proxy_server)}")
            return None
    except KeyError as e:
        st.error(f"❌ Proxy configuration key missing in st.secrets: '{e}'. Check [brightdata_booking] section and 'proxy' key.")
        print(f"❌ Proxy configuration key missing in st.secrets: '{e}'. Check [brightdata_booking] section and 'proxy' key.")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error loading proxy configuration: {e}")
        print(f"❌ Unexpected error loading proxy configuration: {e}")
        traceback.print_exc()
        return None

# ════════════════════════════════════════════════════
# 🌐 Detectar IP real (sin proxy)
# ════════════════════════════════════════════════════
def detectar_ip_real():
    """Detects the machine's public IP address without using a proxy."""
    try:
        # Using httpbin.org/ip as a reliable IP detection service
        print("🌐 Requesting real IP from httpbin.org...")
        response = requests.get("https://httpbin.org/ip", timeout=15) # Increased timeout slightly
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        ip_data = response.json()
        ip_real = ip_data.get("origin", "desconocida")
        # Handle potential comma-separated IPs (take the first one)
        if isinstance(ip_real, str) and ',' in ip_real:
            ip_real = ip_real.split(',')[0].strip()
        print(f"✅ IP Real (sin proxy) detectada: {ip_real}")
        st.session_state["ip_real"] = ip_real
    except requests.exceptions.Timeout:
        print("⚠️ Timeout obteniendo IP real desde httpbin.org.")
        st.session_state["ip_real"] = "error_timeout"
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error de red obteniendo IP real: {e}")
        st.session_state["ip_real"] = "error_request"
    except json.JSONDecodeError:
        print("⚠️ Error decodificando JSON de respuesta de IP real.")
        st.session_state["ip_real"] = "error_json_decode"
    except Exception as e:
        print(f"⚠️ Error inesperado obteniendo IP real: {e}")
        traceback.print_exc()
        st.session_state["ip_real"] = "error_inesperado"

# ════════════════════════════════════════════════════
# 🔎 Verificar IP pública (con proxy, usando Playwright page)
# ════════════════════════════════════════════════════
async def verificar_ip_con_proxy(page):
    """Verifies the public IP address seen by the provided Playwright page."""
    ip_actual = "error_verificacion_inicial"
    try:
        print("🔎 Navegando a httpbin.org/ip con proxy para verificar IP...")
        # Use a reliable IP detection service, reasonable timeout
        await page.goto("https://httpbin.org/ip", timeout=45000, wait_until="domcontentloaded") # Increased timeout
        print("✅ Navegación a httpbin.org completada.")
        # Get content and parse JSON
        ip_info_text = await page.inner_text("body")
        # Check if content looks like JSON before parsing
        if ip_info_text and ip_info_text.strip().startswith('{'):
            ip_json = json.loads(ip_info_text)
            ip_actual = ip_json.get("origin", "desconocida_en_json")
            # Handle potential comma-separated IPs
            if isinstance(ip_actual, str) and ',' in ip_actual:
                 ip_actual = ip_actual.split(',')[0].strip()
            print(f"✅ IP pública detectada (con proxy): {ip_actual}")
        else:
             print(f"⚠️ Contenido inesperado recibido de httpbin.org (no JSON): {ip_info_text[:100]}...")
             ip_actual = "error_contenido_no_json"

    except PlaywrightTimeoutError as e:
        print(f"⚠️ Timeout ({e.timeout/1000.0}s) verificando IP pública con proxy.")
        ip_actual = "error_timeout_verificacion"
    except json.JSONDecodeError as e:
         print(f"⚠️ Error decodificando JSON de IP pública con proxy: {e}")
         ip_actual = "error_json_decode_verificacion"
    except PlaywrightError as e: # Catch specific Playwright errors
         print(f"⚠️ Error de Playwright ({type(e).__name__}) verificando IP pública con proxy: {e}")
         ip_actual = f"error_playwright_{type(e).__name__}"
    except Exception as e:
        print(f"⚠️ Error general verificando IP pública con proxy: {type(e).__name__} - {e}")
        traceback.print_exc()
        ip_actual = f"error_general_{type(e).__name__}"
    finally:
         # Always update session state with the result (even if it's an error code)
         st.session_state["ip_con_proxy"] = ip_actual
         print(f"ℹ️ Estado de sesión 'ip_con_proxy' actualizado a: {ip_actual}")
         return ip_actual # Return the detected IP or error code

# ════════════════════════════════════════════════════
# 📅 Scraping Booking usando Playwright + Proxy (Single URL Task)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance=None):
    """
    Extrae datos de una URL de Booking.com.
    Puede usar una instancia de navegador existente o crear una nueva.
    """
    html = ""
    close_browser_on_finish = False
    current_p = None

    try:
        if not browser_instance:
            close_browser_on_finish = True
            current_p = await async_playwright().start()
            
            # Obtener y verificar la configuración del proxy
            browser_config = ProxyConfig.get_playwright_browser_config()
            if not browser_config.get('proxy'):
                st.error("❌ No se pudo configurar el proxy. Verificando configuración actual:")
                st.write(ProxyConfig.get_proxy_settings())
                return {"error": "Configuración de proxy no válida"}, ""
            
            print(f"🔄 Iniciando navegador con proxy: {browser_config['proxy']['server']}")
            browser_instance = await current_p.chromium.launch(**browser_config)

        # Crear un nuevo contexto con configuración específica
        context = await browser_instance.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES",
            ignore_https_errors=True  # Importante para algunos proxies
        )
        
        # Habilitar logging de red para debug
        await context.route("**/*", lambda route: print(f"🌐 Solicitud a: {route.request.url}") or route.continue_())
        
        page = await context.new_page()
        await page.set_extra_http_headers({
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        })

        print(f"🔄 Navegando a: {url}")
        try:
            response = await page.goto(url, timeout=90000, wait_until="networkidle")
            if not response:
                print("❌ No se recibió respuesta de la página")
                return {"error": "No response"}, ""
            
            print(f"✅ Respuesta recibida. Status: {response.status}")
            if response.status != 200:
                print(f"⚠️ Status code inesperado: {response.status}")
                return {"error": f"Status code: {response.status}"}, ""
                
        except PlaywrightTimeoutError:
            print("⚠️ Timeout en networkidle, intentando con domcontentloaded...")
            response = await page.goto(url, timeout=90000, wait_until="domcontentloaded")
            if not response or response.status != 200:
                print(f"❌ Error en segundo intento. Status: {response.status if response else 'No response'}")

        # Esperas y verificaciones
        try:
            print("🔄 Esperando selector JSON-LD...")
            await page.wait_for_selector('script[type="application/ld+json"]', timeout=20000)
            print("✅ Selector JSON-LD encontrado")
        except PlaywrightTimeoutError:
            print("⚠️ Timeout esperando JSON-LD. Continuando...")

        # Esperar a que la red esté inactiva
        try:
            print("🔄 Esperando a que la red esté inactiva...")
            await page.wait_for_load_state("networkidle", timeout=30000)
            print("✅ Red inactiva")
        except Exception as e:
            print(f"⚠️ Error esperando networkidle: {e}")

        html = await page.content()
        await context.close()

    except PlaywrightTimeoutError as e:
        print(f"❌ Timeout de Playwright ({getattr(e, 'timeout', 'N/A')/1000.0}s) durante la operación en {url}.")
        return {
            "error": "Timeout de Playwright",
            "url": url,
            "details": f"Timeout ({getattr(e, 'timeout', 'N/A')}ms): {str(e)}"
        }, ""
    except PlaywrightError as e: # Catch specific Playwright errors
        print(f"❌ Error de Playwright ({type(e).__name__}) durante scraping de {url}: {e}")
        traceback.print_exc()
        return {
            "error": f"Error de Playwright ({type(e).__name__})",
            "url": url,
            "details": f"{type(e).__name__}: {str(e)}"
        }, ""
    except Exception as e:
        print(f"❌ Error inesperado durante scraping de {url}: {type(e).__name__} - {e}")
        traceback.print_exc()
        return {
            "error": "Error inesperado en scraping",
            "url": url,
            "details": f"{type(e).__name__}: {str(e)}"
        }, ""

    # --- Check if HTML is empty after supposed success ---
    if not html:
         print(f"❌ HTML vacío obtenido para {url} después de un intento aparentemente exitoso.")
         return {
             "error": "HTML vacío inesperado",
             "url": url
         }, ""

    # --- Parse HTML ---
    print(f"⚙️ Parseando HTML para {url}...")
    try:
        soup = BeautifulSoup(html, "html.parser")
        # Pass IPs explicitly or let parse_html fetch from session_state
        resultado = parse_html_booking(soup, url, st.session_state.get("ip_real", "error_no_detectada_previamente"), st.session_state.get("ip_con_proxy", "no_verificada_aun"))
        print(f"✅ Parseo completado para {url}.")
        return resultado, html # Return parsed data and html
    except Exception as parse_e:
         print(f"❌ Error durante el parseo de HTML para {url}: {parse_e}")
         traceback.print_exc()
         return {
             "error": "Error en parseo HTML",
             "url": url,
             "details": f"ParseError: {str(parse_e)}"
         }, ""


# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking
# ════════════════════════════════════════════════════
# Modified to accept IPs as arguments for clarity
def parse_html_booking(soup, url, ip_real, ip_con_proxy):
    """Parses the BeautifulSoup object to extract hotel data."""
    print(f"ℹ️ Iniciando parseo para {url} con IPs: Real={ip_real}, Proxy={ip_con_proxy}")
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Extract details from URL parameters
    group_adults = query_params.get('group_adults', [''])[0]
    group_children = query_params.get('group_children', [''])[0]
    no_rooms = query_params.get('no_rooms', [''])[0]
    dest_type = query_params.get('dest_type', [''])[0]
    # Extract checkin/checkout if present, otherwise use default logic
    checkin_url = query_params.get('checkin', [None])[0]
    checkout_url = query_params.get('checkout', [None])[0]

    # Default dates if not in URL
    default_checkin = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    default_checkout = (datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d")

    data_extraida = {}
    imagenes_secundarias = []
    servicios = []

    # --- Extract JSON-LD ---
    try:
        scripts_ldjson = soup.find_all('script', type='application/ld+json')
        found_hotel_ld = False
        for script in scripts_ldjson:
            if script.string:
                try:
                    data_json = json.loads(script.string)
                    # Handle cases where JSON-LD is a list or a single object
                    items_to_check = data_json if isinstance(data_json, list) else [data_json]
                    for item in items_to_check:
                        if isinstance(item, dict) and item.get("@type") in ["Hotel", "Hostel", "BedAndBreakfast", "Apartment"]: # Expand types if needed
                            data_extraida = item
                            found_hotel_ld = True
                            print(f"✅ Datos JSON-LD ({item.get('@type')}) encontrados.")
                            break # Found the main hotel data
                    if found_hotel_ld: break # Exit outer loop too
                except json.JSONDecodeError:
                    print("⚠️ Error decodificando un script JSON-LD, saltando.")
                    continue
                except Exception as ld_inner_e:
                     print(f"⚠️ Error procesando un script JSON-LD: {ld_inner_e}")
                     continue
        if not found_hotel_ld:
             print("⚠️ No se encontró JSON-LD con @type 'Hotel' (u otros tipos relevantes).")
    except Exception as e:
        print(f"❌ Error buscando scripts JSON-LD: {e}")
        traceback.print_exc()


    # --- Extract Images (Alternative Method if JSON-LD fails or lacks images) ---
    # Often images are in standard <img> tags or background styles
    # Let's try finding primary image gallery thumbnails if they exist
    try:
        # Look for thumbnail links (selectors might change based on Booking.com layout)
        thumb_links = soup.select('a[data-preview-url-template]') # Example selector
        for link in thumb_links:
             img_url = link.get('data-preview-url-template')
             if img_url and isinstance(img_url, str) and len(imagenes_secundarias) < 15: # Get up to 15
                 # Often these URLs have placeholders like {width}x{height}
                 # Replace with a reasonable size like max1024x768 if needed, or use as is
                 img_url_formatted = img_url.replace("{width}x{height}", "max1024x768") # Example formatting
                 if img_url_formatted not in imagenes_secundarias:
                    imagenes_secundarias.append(img_url_formatted)

        if imagenes_secundarias:
             print(f"✅ Encontradas {len(imagenes_secundarias)} imágenes (método alternativo).")
        else:
             print("⚠️ No se encontraron imágenes con el método alternativo.")
             # You could add the JSON script search here as a fallback if needed

    except Exception as e:
        print(f"⚠️ Error buscando imágenes (método alternativo): {e}")
        traceback.print_exc()


    # --- Extract Amenities/Services (Refined Selector) ---
    try:
        # Try finding the main facilities block first (more reliable)
        facilities_block = soup.find('div', class_=lambda x: x and 'hp_desc_important_facilities' in x) # More general class finder
        processed_facilities = False
        if facilities_block:
             # Find individual facilities within the block
             # Common pattern: list items or divs with specific icons/text spans
             svc_elements = facilities_block.find_all(['li', 'span'], class_=lambda x: x and ('popular_facility' in x or 'facility' in x)) # Broader search
             for svc in svc_elements:
                 texto = svc.get_text(strip=True)
                 if texto and texto not in servicios and len(texto) > 2: # Avoid empty/short strings
                     servicios.append(texto)
             if servicios:
                 print(f"✅ Encontrados {len(servicios)} servicios/facilidades (bloque principal).")
                 processed_facilities = True

        # Fallback if the main block isn't found or yields no results
        if not processed_facilities:
             print("ℹ️ Bloque principal de facilidades no encontrado o vacío, intentando con clase genérica 'bui-list__description'...")
             # Fallback to the original generic class
             svc_elements = soup.find_all('div', class_="bui-list__description")
             for svc in svc_elements:
                 texto = svc.get_text(strip=True)
                 if texto and texto not in servicios and len(texto) > 2:
                      servicios.append(texto)
             if servicios:
                 print(f"✅ Encontrados {len(servicios)} servicios (método fallback).")

        if not servicios:
             print("⚠️ No se encontraron servicios con ninguno de los métodos probados.")

    except Exception as e:
        print(f"⚠️ Error extrayendo servicios: {e}")
        traceback.print_exc()


    # --- Consolidate Results ---
    address_info = data_extraida.get("address", {}) if isinstance(data_extraida.get("address"), dict) else {}
    rating_info = data_extraida.get("aggregateRating", {}) if isinstance(data_extraida.get("aggregateRating"), dict) else {}


    return {
        "ip_real": ip_real, # Passed as argument
        "ip_con_proxy": ip_con_proxy, # Passed as argument
        "url_original": url,
        "timestamp_scraping": datetime.datetime.now().isoformat(),
        "checkin": checkin_url or default_checkin,
        "checkout": checkout_url or default_checkout,
        "group_adults": group_adults,
        "group_children": group_children,
        "no_rooms": no_rooms,
        "dest_type": dest_type,
        # Data from JSON-LD (with fallbacks)
        "nombre_alojamiento": data_extraida.get("name") or (soup.find("h1").get_text(strip=True) if soup.find("h1") else None),
        "direccion": address_info.get("streetAddress"),
        "codigo_postal": address_info.get("postalCode"),
        "ciudad": address_info.get("addressLocality"),
        "pais": address_info.get("addressCountry", {}).get("name") if isinstance(address_info.get("addressCountry"), dict) else address_info.get("addressCountry"),
        "tipo_alojamiento": data_extraida.get("@type"),
        "descripcion_corta": data_extraida.get("description"),
        "valoracion_global": rating_info.get("ratingValue"),
        "numero_opiniones": rating_info.get("reviewCount"),
        # Data from scraping
        "imagenes": data_extraida.get("image") or imagenes_secundarias, # Prefer JSON-LD image if available
        "servicios": servicios,
        "titulo_h1": soup.find("h1").get_text(strip=True) if soup.find("h1") else None,
        "bloques_contenido_h2": [h2.get_text(strip=True) for h2 in soup.find_all("h2")],
    }


# ════════════════════════════════════════════════════
# 🗂️ Procesar varias URLs en lote (Optimized)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar):
    """Processes a list of URLs in batch using a single browser instance."""
    tasks_results = []
    playwright_instance = None
    browser = None

    print("\n--- Iniciando proceso en lote ---")
    # --- Detect Real IP Once before starting ---
    detectar_ip_real()
    ip_real_detectada = st.session_state.get("ip_real", "error_pre_lanzamiento")
    print(f"ℹ️ IP Real detectada para el lote: {ip_real_detectada}")
    if ip_real_detectada.startswith("error_"):
         st.warning(f"⚠️ No se pudo detectar la IP real ({ip_real_detectada}). La comparación con IP de proxy no será posible.")


    # --- Get Proxy Settings ---
    proxy_config = get_proxy_settings()
    if not proxy_config:
        st.error("❌ Fallo crítico: No se pudo cargar la configuración del proxy desde secrets.toml. Abortando proceso en lote.")
        # Return errors for all URLs immediately
        for u_err in urls_a_procesar:
             tasks_results.append({
                 "error": "Fallo carga configuración proxy (secrets.toml)",
                 "ip_real": ip_real_detectada,
                 "ip_con_proxy": "no_intentado",
                 "url": u_err
                 })
        return tasks_results

    # --- Launch Playwright and Browser Once ---
    try:
        print("🚀 Iniciando Playwright y Navegador global para el lote (con proxy)...")
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(
            headless=True, # Set to False for debugging if needed
            proxy=proxy_config,
            # slow_mo=50 # Uncomment to slow down operations for debugging (milliseconds)
        )
        print("✅ Navegador global para lote lanzado con proxy.")

        # --- Create and Run Tasks Concurrently ---
        print(f"🌀 Creando {len(urls_a_procesar)} tareas de scraping...")
        # Pass the shared browser instance to each task
        tasks = [obtener_datos_booking_playwright(u, browser_instance=browser) for u in urls_a_procesar]
        # Execute tasks concurrently
        tasks_results_with_html = await asyncio.gather(*tasks, return_exceptions=True)
        print("🏁 Todas las tareas han finalizado.")

        # --- Process Results ---
        print("\n--- Procesando resultados del lote ---")
        for i, res_or_exc in enumerate(tasks_results_with_html):
            url_procesada = urls_a_procesar[i] # Get corresponding URL
            print(f"🔍 Procesando resultado para: {url_procesada}")

            if isinstance(res_or_exc, Exception):
                # This catches exceptions *raised by asyncio.gather itself* or critical unhandled exceptions within the task
                st.error(f"❌ Error crítico no capturado en task para {url_procesada}: {type(res_or_exc).__name__} - {res_or_exc}")
                traceback.print_exc()
                tasks_results.append({
                    "error": f"Excepción crítica no capturada ({type(res_or_exc).__name__})",
                    "url": url_procesada,
                    "ip_real": st.session_state.get("ip_real", "error_excepcion_gather"),
                    "ip_con_proxy": st.session_state.get("ip_con_proxy", "error_excepcion_gather"), # Get last known proxy IP state
                    "details": str(res_or_exc)
                })
            elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                # Task completed and returned (result_dict, html_content)
                resultado_item, html_content_item = res_or_exc
                tasks_results.append(resultado_item) # Append the dictionary part
                if isinstance(resultado_item, dict) and not resultado_item.get("error"):
                    # Store HTML only if scraping was successful for that item
                    st.session_state.last_successful_html_content = html_content_item
                    print(f"✅ Resultado exitoso guardado para {url_procesada}")
                elif isinstance(resultado_item, dict):
                     print(f"ℹ️ Resultado con error reportado para {url_procesada}: {resultado_item.get('error', 'Sin error explícito')}")
                else:
                     # Handle unexpected format if resultado_item is not a dict
                     print(f"⚠️ Formato de resultado inesperado (no dict) para {url_procesada}: {type(resultado_item)}")
                     tasks_results[-1] = {"error": "Formato resultado inesperado", "url": url_procesada, "details": str(resultado_item)}

            else:
                # Task completed but returned something unexpected
                st.warning(f"⚠️ Resultado inesperado (no tupla de 2) recibido de task para {url_procesada}: {res_or_exc}")
                tasks_results.append({
                    "error": "Resultado inesperado de la tarea (formato)",
                    "url": url_procesada,
                     "ip_real": st.session_state.get("ip_real", "error_formato_inesperado"),
                     "ip_con_proxy": st.session_state.get("ip_con_proxy", "error_formato_inesperado"),
                     "details": str(res_or_exc)
                    })

    except PlaywrightError as e_launcher: # Catch Playwright-specific errors during launch
        st.error(f"❌ Error crítico de Playwright al iniciar el navegador para el lote: {type(e_launcher).__name__} - {e_launcher}")
        print(f"❌ Error crítico de Playwright al iniciar el navegador para el lote: {type(e_launcher).__name__} - {e_launcher}")
        traceback.print_exc()
        # If browser launch fails, create error results for all URLs
        tasks_results = [] # Reset results as none could be processed
        for u_err in urls_a_procesar:
            tasks_results.append({
                "error": f"Fallo inicio navegador Playwright ({type(e_launcher).__name__})",
                "url": u_err,
                 "ip_real": st.session_state.get("ip_real", "error_fallo_navegador"),
                 "ip_con_proxy": "no_intentado",
                "details": str(e_launcher)
            })
    except Exception as e_launcher: # Catch other potential errors during setup
        st.error(f"❌ Error crítico general al configurar el lote: {type(e_launcher).__name__} - {e_launcher}")
        print(f"❌ Error crítico general al configurar el lote: {type(e_launcher).__name__} - {e_launcher}")
        traceback.print_exc()
        tasks_results = [] # Reset results
        for u_err in urls_a_procesar:
            tasks_results.append({
                "error": f"Fallo general configuración lote ({type(e_launcher).__name__})",
                "url": u_err,
                 "ip_real": st.session_state.get("ip_real", "error_fallo_general_lote"),
                 "ip_con_proxy": "no_intentado",
                "details": str(e_launcher)
            })
    finally:
        # --- Ensure browser and playwright are closed ---
        print("\n--- Limpiando recursos del lote ---")
        if browser:
            try:
                await browser.close()
                print("✅ Navegador global cerrado.")
            except Exception as browser_close_e:
                 print(f"⚠️ Error cerrando navegador global: {browser_close_e}")
                 traceback.print_exc()
        if playwright_instance:
            try:
                 await playwright_instance.stop()
                 print("✅ Playwright global detenido.")
            except Exception as pw_stop_e:
                 print(f"⚠️ Error deteniendo Playwright global: {pw_stop_e}")
                 traceback.print_exc()
        print("--- Fin del proceso en lote ---")

    return tasks_results


# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (UI and Control Flow)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    """Renders the Streamlit UI and orchestrates the scraping process."""
    st.session_state.setdefault("_called_script", "scraping_booking")
    st.title("🏨 Scraping hoteles Booking (BrightData + Playwright)")
    st.caption("Introduce URLs de hoteles de Booking.com para extraer datos usando un proxy BrightData.")

    # --- Initialize Session State Keys ---
    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/barcelo-tenerife-royal-level.es.html?checkin=2025-05-12&checkout=2025-05-13&group_adults=2&group_children=0&no_rooms=1&dest_id=-369166&dest_type=city") # Example URL
    st.session_state.setdefault("resultados_json", [])
    st.session_state.setdefault("last_successful_html_content", "")
    st.session_state.setdefault("ip_real", "no_detectada_aun")
    st.session_state.setdefault("ip_con_proxy", "no_verificada_aun")
    st.session_state.setdefault("scraping_in_progress", False)

    # --- Input Area ---
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150,
        key="urls_input_area",
        disabled=st.session_state.scraping_in_progress,
        help="Asegúrate de que cada URL esté en una línea separada y sea una URL válida de Booking.com."
    )

    # --- Control Buttons ---
    col1, col2, col3 = st.columns([1.5, 1, 1]) # Adjust column ratios if needed

    with col1:
        buscar_btn_pressed = st.button(
            "🔍 Scrapear hoteles",
            key="buscar_hoteles_booking",
            disabled=st.session_state.scraping_in_progress or not st.session_state.urls_input.strip(),
            help="Inicia el proceso de scraping para las URLs introducidas."
            )

    # --- Scraping Execution Logic ---
    if buscar_btn_pressed:
        urls_raw = st.session_state.urls_input.strip().split("\n")
        urls = [url.strip() for url in urls_raw if url.strip() and url.startswith("https://www.booking.com")] # Basic validation

        if urls:
            st.session_state.scraping_in_progress = True
            st.session_state.resultados_json = [] # Clear previous results
            st.session_state.last_successful_html_content = "" # Clear previous HTML
            st.info(f"Iniciando scraping para {len(urls)} URL(s)... Verifica la consola para logs detallados.")
            # Display placeholder for IPs
            ip_status_placeholder = st.empty()
            ip_status_placeholder.write(f"IP Real: Detectando... | IP Proxy: Verificando...")

            # Run the batch processing in an asyncio event loop
            with st.spinner(f"🔄 Scrapeando {len(urls)} hoteles... (Esto puede tardar)"):
                 try:
                    # Run the async function
                    resultados_lote = asyncio.run(procesar_urls_en_lote(urls))
                    st.session_state.resultados_json = resultados_lote
                    st.success(f"✅ Proceso completado para {len(urls)} URL(s).")
                 except RuntimeError as e:
                      if "cannot run current event loop" in str(e):
                           st.error("❌ Error de Bucle de Eventos: Streamlit puede tener conflictos con asyncio.run(). Intenta reiniciar la app.")
                           print("❌ Error de Bucle de Eventos: Streamlit puede tener conflictos con asyncio.run(). Considera nest_asyncio si el problema persiste.")
                           st.session_state.resultados_json = [{"error": "Fallo ejecución asyncio (RuntimeError)", "details": str(e)}]
                      else:
                           st.error(f"❌ Error inesperado al ejecutar el proceso asíncrono: {e}")
                           traceback.print_exc()
                           st.session_state.resultados_json = [{"error": "Fallo ejecución asyncio", "details": str(e)}]
                 except Exception as run_e:
                      st.error(f"❌ Error general al ejecutar el proceso asíncrono: {run_e}")
                      traceback.print_exc()
                      st.session_state.resultados_json = [{"error": "Fallo ejecución asyncio (General)", "details": str(run_e)}]

            # Update IP display after completion
            ip_status_placeholder.write(
                f"IP Real (final): `{st.session_state.get('ip_real', 'Error')}` | "
                f"IP Proxy (final): `{st.session_state.get('ip_con_proxy', 'Error')}`"
            )
            st.session_state.scraping_in_progress = False
            st.rerun() # Rerun to update the UI state correctly after scraping finishes

        else:
            st.warning("Por favor, introduce al menos una URL válida de Booking.com.")


    # --- Display Results and Export/Upload Buttons ---
    if st.session_state.resultados_json and not st.session_state.scraping_in_progress:
        # Filter results
        resultados_validos = [r for r in st.session_state.resultados_json if isinstance(r, dict) and not r.get("error")]
        resultados_con_error = [r for r in st.session_state.resultados_json if isinstance(r, dict) and r.get("error")]

        st.subheader(f"📊 Resumen: {len(resultados_validos)} Éxitos, {len(resultados_con_error)} Errores")

        # Buttons only appear if there are valid results
        if resultados_validos:
            nombre_archivo_base = f"datos_hoteles_booking_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            contenido_json_validos = json.dumps(resultados_validos, ensure_ascii=False, indent=2).encode("utf-8")

            with col2: # Use the columns defined earlier
                st.download_button(
                    label="⬇️ Exportar Éxitos (JSON)",
                    data=contenido_json_validos,
                    file_name=f"{nombre_archivo_base}_exitos.json",
                    mime="application/json",
                    key="descargar_json_exitos",
                    help="Descarga los resultados exitosos como un archivo JSON."
                )

            with col3: # Use the columns defined earlier
                subir_a_drive_btn = st.button("☁️ Subir Éxitos a Drive", key="subir_drive_booking_exitos", help="Sube los resultados exitosos a Google Drive (si está configurado).")
                if subir_a_drive_btn:
                    with st.spinner("☁️ Subiendo a Google Drive..."):
                        # Assuming subir_resultado_a_drive is defined elsewhere and handles bytes
                        subir_resultado_a_drive(f"{nombre_archivo_base}_exitos.json", contenido_json_validos)

        elif not resultados_con_error: # No errors, but also no valid results (e.g., empty input initially)
             pass # Don't show the info message if there are simply no results yet
        else: # Only errors, no valid results
             with col2:
                  st.info("No hay resultados exitosos para exportar/subir.")


        # --- Display Detailed Results (including errors) ---
        with st.expander("📦 Ver Resultados Detallados (JSON)", expanded=False):
             st.json(st.session_state.resultados_json)

        # --- Display Last Successful HTML ---
        if st.session_state.last_successful_html_content:
            st.subheader("📄 HTML capturado (última URL exitosa)")
            with st.expander("👁️ Ver/Descargar HTML", expanded=False):
                st.text_area("HTML Content", st.session_state.last_successful_html_content, height=300, key="html_view_area")
                st.download_button(
                    label="⬇️ Descargar HTML",
                    data=st.session_state.last_successful_html_content.encode("utf-8"),
                    file_name=f"pagina_booking_exitosa_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    key="descargar_html_exitoso"
                 )

# ════════════════════════════════════════════════════
# ☁️ Helper for Drive Upload (Example Structure)
# ════════════════════════════════════════════════════
def subir_resultado_a_drive(nombre_archivo, contenido_bytes):
    """Placeholder for your Google Drive upload logic."""
    try:
        print(f"☁️ Iniciando subida a Drive: {nombre_archivo} ({len(contenido_bytes)} bytes)...")
        # --- Replace with your actual Google Drive API call ---
        # Example using hypothetical functions from your drive_utils
        folder_name = "Scraping Booking Resultados" # Define your target folder
        folder_id = obtener_o_crear_subcarpeta(folder_name) # Get folder ID
        if not folder_id:
             raise ValueError(f"No se pudo obtener o crear la carpeta de Drive: {folder_name}")

        file_metadata = {'name': nombre_archivo, 'parents': [folder_id]}
        # Assuming subir_json_a_drive takes metadata and bytes content
        file_info = subir_json_a_drive(file_metadata, contenido_bytes)
        # --- End of placeholder section ---

        if file_info: # Check if upload function returned success indicator
             st.success(f"✅ Archivo '{nombre_archivo}' subido a Google Drive.")
             print(f"✅ Archivo '{nombre_archivo}' subido a Google Drive.")
        else:
             st.error("❌ La subida a Drive no devolvió confirmación.")
             print("❌ La subida a Drive no devolvió confirmación.")

    except ImportError:
         st.error("❌ Error: Módulo 'drive_utils' o sus dependencias no encontrados. La subida a Drive falló.")
         print("❌ Error: Módulo 'drive_utils' o sus dependencias no encontrados.")
    except Exception as e:
        st.error(f"❌ Error subiendo a Google Drive: {e}")
        print(f"❌ Error subiendo a Google Drive: {e}")
        traceback.print_exc()

# ════════════════════════════════════════════════════
# Entry Point for Streamlit
# ════════════════════════════════════════════════════
if __name__ == "__main__":
    # When running streamlit run your_app.py, Streamlit typically discovers and runs
    # functions based on the script structure or explicit calls.
    # Calling the main render function here ensures it runs.
    render_scraping_booking()

async def verificar_proxy():
    """Verifica si el proxy está funcionando correctamente."""
    print("🔄 Verificando configuración del proxy...")
    
    try:
        async with async_playwright() as p:
            browser_config = ProxyConfig.get_playwright_browser_config()
            if not browser_config.get('proxy'):
                st.error("❌ No se pudo obtener la configuración del proxy")
                return False

            browser = await p.chromium.launch(**browser_config)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            # Intentar obtener la IP actual
            try:
                response = await page.goto('https://api.ipify.org?format=json', timeout=30000)
                if response.ok:
                    data = await response.json()
                    ip = data.get('ip')
                    print(f"✅ IP detectada a través del proxy: {ip}")
                    st.success(f"Proxy funcionando correctamente. IP: {ip}")
                    return True
                else:
                    print(f"❌ Error obteniendo IP. Status: {response.status}")
                    st.error(f"Error verificando proxy. Status code: {response.status}")
            except Exception as e:
                print(f"❌ Error verificando proxy: {e}")
                st.error(f"Error verificando proxy: {str(e)}")
            finally:
                await browser.close()
    except Exception as e:
        print(f"❌ Error general verificando proxy: {e}")
        st.error(f"Error general verificando proxy: {str(e)}")
    
    return False

def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping hoteles Booking")

    # Añadir botón para verificar proxy
    if st.button("🔍 Verificar Proxy"):
        with st.spinner("Verificando proxy..."):
            asyncio.run(verificar_proxy())

    # ... rest of the existing code ...