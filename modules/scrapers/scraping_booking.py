import streamlit as st
import asyncio
import json
import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# ... (get_proxy_settings se mantiene igual) ...

# ════════════════════════════════════════════════════
# 📅 Scraping Booking (Playwright - PRUEBA 4: Bloqueo Condicional)
# ════════════════════════════════════════════════════
async def obtener_datos_booking_playwright(url: str, browser_instance, block_aggressively: bool): # Nuevo parámetro
    """PRUEBA 4: Aplica bloqueo de recursos condicional."""
    html = ""
    page = None
    resultado_final = {}
    request_counter_list = [0] 
    blocked_counter_list = [0]

    try:
        page = await browser_instance.new_page(ignore_https_errors=True)
        
        page.on("request", lambda req: request_counter_list[0] += 1)
        
        # --- OPTIMIZACIÓN: PRUEBA 4 - Bloqueo CONDICIONAL ---
        if block_aggressively:
            print(f"Configurando bloqueo AGRESIVO para (con proxy): {url}")
            DOMINIOS_GENERALES_A_BLOQUEAR = [ # Lista para el bloqueo agresivo
                "googletagmanager.com", "google-analytics.com", "analytics.google.com",
                "googletagservices.com", "tealiumiq.com", "tags.tiqcdn.com", 
                "adobedtm.com", "assets.adobedtm.com", "omtrdc.net", "dpm.demdex.net",
                "googlesyndication.com", "doubleclick.net", "adservice.google.com",
                "connect.facebook.net", "staticxx.facebook.com", "www.facebook.com/tr/",
                "criteo.com", "criteo.net", "static.criteo.net", "targeting.criteo.com",
                "adnxs.com", "optimizely.com", "scorecardresearch.com", "sb.scorecardresearch.com",
                "everesttech.net", "creativecdn.com", "yieldlab.net",
                "bing.com/ads", "bat.bing.com", "ads.microsoft.com",
                "cookielaw.org", "cdn.cookielaw.org", "onetrust.com", 
                "usercentrics.com", "app.usercentrics.eu",
                "krxd.net", "rlcdn.com", "casalemedia.com", "pubmatic.com", 
                "amazon-adsystem.com", "adsystem.amazon.com", "aax.amazon-adsystem.com",
                "nr-data.net",
            ]
            PATRONES_URL_A_BLOQUEAR_GENERAL = [
                "/tracking", "/analytics", "/ads", "/advert", "/banner",
                "beacon", "pixel", "collect", "gtm.js", "sdk.js",
                "optanon", "usercentrics", "challenge.js", "OtAutoBlock.js", "otSDKStub.js"
            ]

            def should_block_aggressively(request_obj):
                res_type = request_obj.resource_type
                res_url = request_obj.url.lower()
                if res_type in ["image", "font", "media", "stylesheet"]: # Bloquear CSS en modo agresivo
                    blocked_counter_list[0] += 1
                    return True
                if res_type in ["script", "xhr", "fetch"]:
                    if "booking.com" in res_url or "bstatic.com" in res_url: 
                        for pattern in PATRONES_URL_A_BLOQUEAR_GENERAL: # Aplicar patrones a booking también
                            if pattern in res_url:
                                blocked_counter_list[0] += 1
                                return True
                        return False 
                    for domain in DOMINIOS_GENERALES_A_BLOQUEAR:
                        if domain in res_url: blocked_counter_list[0] += 1; return True
                    for pattern in PATRONES_URL_A_BLOQUEAR_GENERAL:
                        if pattern in res_url: blocked_counter_list[0] += 1; return True
                return False
            await page.route("**/*", lambda route: route.abort() if should_block_aggressively(route.request) else route.continue_())
            print("Bloqueo AGRESIVO (con proxy) configurado.")
        else: # Bloqueo LIGERO para el intento SIN proxy
            print(f"Configurando bloqueo LIGERO para (sin proxy): {url}")
            await page.route("**/*", 
                lambda route: route.abort() if route.request.resource_type in [
                    "image", # Bloquear solo imágenes y fuentes
                    "font",
                    "media" 
                    # PERMITIR stylesheet y TODOS los scripts/xhr/fetch en este modo
                ] else route.continue_()
            )
            print("Bloqueo LIGERO (sin proxy) configurado.")
        # --- Fin Optimización ---

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8" })
        
        print(f"Navegando a: {url} (Modo agresivo: {block_aggressively})")
        await page.goto(url, timeout=100000, wait_until="domcontentloaded")
        
        try:
            selector_estable = "#hp_hotel_name" 
            print(f"Esperando selector estable: '{selector_estable}' para {url}")
            await page.wait_for_selector(selector_estable, state="visible", timeout=35000)
            print(f"Selector estable encontrado para {url}.")
        except PlaywrightTimeoutError:
            print(f"Advertencia: Selector estable '{selector_estable}' no encontrado en 35s para {url}.")
        
        html = await page.content()
        
        request_count = request_counter_list[0]
        if block_aggressively: # Solo contamos bloqueados si el bloqueo agresivo estuvo activo
            blocked_request_count = blocked_counter_list[0]
        else: # Si el bloqueo fue ligero, no tenemos un contador separado de bloqueados para ese modo
            blocked_request_count = 0 # Asumimos que los bloqueados en modo ligero son solo los de tipo general

        print(f"HTML obtenido para {url} (Tamaño: {len(html)} bytes). Iniciados: {request_count}, Bloqueados (aprox): {blocked_request_count}")
        
        if not html or (not block_aggressively and "<noscript>" in html.lower() and "javascript is disabled" in html.lower()):
            details_error = "No se obtuvo contenido HTML."
            if not block_aggressively and "<noscript>" in html.lower():
                details_error = "Página devolvió error de JavaScript deshabilitado (intento sin proxy)."
                print(f"Error JavaScript deshabilitado para {url}.")
            else:
                print(f"Error: HTML vacío para {url}.")
            return {"error": "Fallo_HTML_Playwright", "url_original": url, "details": details_error, "request_count_total_iniciados": request_count, "request_count_bloqueados": blocked_request_count, "request_count_netos_estimados": request_count - blocked_request_count}, ""
        
        soup = BeautifulSoup(html, "html.parser")
        resultado_final = parse_html_booking(soup, url)
        if isinstance(resultado_final, dict):
            resultado_final["request_count_total_iniciados"] = request_count
            resultado_final["request_count_bloqueados"] = blocked_request_count
            resultado_final["request_count_netos_estimados"] = request_count - blocked_request_count
        
    # ... (los bloques except se mantienen similares, solo actualiza el nombre del método en los prints si quieres) ...
    except PlaywrightTimeoutError as e:
        # ...
    except Exception as e:
        # ...
    finally:
        if page:
            try: await page.close()
            except Exception as e: print(f"Error menor al cerrar página {url}: {e}")
    return resultado_final, html

# ════════════════════════════════════════════════════
# 📋 Parsear HTML de Booking (actualizar "metodo_extraccion")
# ════════════════════════════════════════════════════
def parse_html_booking(soup, url):
    # ... (lógica interna igual) ...
    # Solo cambiar el método para reflejar Prueba4
    return {
        # ... otros campos ...
        "metodo_extraccion": "Playwright_Prueba4_BloqueoCondicional",
        # ... resto de campos ...
    }


# ════════════════════════════════════════════════════
# 🗂️ Procesar Lote con Playwright (pasando el flag de bloqueo)
# ════════════════════════════════════════════════════
async def procesar_urls_en_lote(urls_a_procesar, use_proxy: bool, block_resources_aggressively: bool): # Nuevo parámetro
    """Procesa URLs con Playwright, con bloqueo de recursos condicional."""
    tasks_results = []
    proxy_conf_playwright = None
    browser_launch_options = {"headless": True} 

    if use_proxy:
        proxy_conf_playwright = get_proxy_settings()
        if not proxy_conf_playwright:
            print("Error: Proxy requerido pero no configurado.")
            return [{"error": "Proxy requerido pero no configurado", "url_original": url, "details": ""} for url in urls_a_procesar]
        else:
            browser_launch_options["proxy"] = proxy_conf_playwright
            print(f"Lote Playwright: Usando proxy: {proxy_conf_playwright['server']}")
    else:
        print("Lote Playwright: Ejecutando SIN proxy.")

    # La lógica de bloqueo de recursos ahora está dentro de obtener_datos_booking_playwright
    # y se activa con el flag 'block_resources_aggressively'

    async with async_playwright() as p:
        browser = None
        try:
            print(f"Lanzando navegador Playwright (para {'proxy' if use_proxy else 'directo'}, bloqueo agresivo: {block_resources_aggressively})...")
            browser = await p.chromium.launch(**browser_launch_options)
            print("Navegador Playwright lanzado.")
            
            tasks = [obtener_datos_booking_playwright(url, browser, block_aggressively=block_resources_aggressively) for url in urls_a_procesar]
            results_with_exceptions = await asyncio.gather(*tasks, return_exceptions=True)
            
            # ... (procesamiento de results_with_exceptions se mantiene igual) ...
            temp_results = []
            for i, res_or_exc in enumerate(results_with_exceptions):
                url_p = urls_a_procesar[i]
                if isinstance(res_or_exc, Exception):
                    print(f"Excepción en gather (Playwright) para {url_p}: {res_or_exc}")
                    temp_results.append({"error": "Fallo_Excepcion_Gather_Playwright", "url_original": url_p, "details": str(res_or_exc)})
                elif isinstance(res_or_exc, tuple) and len(res_or_exc) == 2:
                    res_dict, html_content = res_or_exc
                    if isinstance(res_dict, dict):
                        temp_results.append(res_dict)
                        if not res_dict.get("error") and html_content:
                            st.session_state.last_successful_html_content = html_content
                    else:
                        temp_results.append({"error": "Fallo_TipoResultadoInesperado_Playwright", "url_original": url_p, "details": f"Tipo: {type(res_dict)}"})
                else:
                    temp_results.append({"error": "Fallo_ResultadoInesperado_Playwright", "url_original": url_p, "details": str(res_or_exc)})
            tasks_results = temp_results

        except Exception as batch_error:
            # ...
        finally:
            # ...
    return tasks_results


# ════════════════════════════════════════════════════
# 🎯 Función principal Streamlit (ajustada para bloqueo condicional)
# ════════════════════════════════════════════════════
def render_scraping_booking():
    st.session_state.setdefault("_called_script", "scraping_booking_playwright_prueba4")
    st.title("🏨 Scraping Hoteles Booking (Playwright Prueba 4)")
    
    # ... (inicialización de session_state igual) ...
    st.session_state.setdefault("urls_input", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    st.session_state.setdefault("resultados_finales", [])
    st.session_state.setdefault("last_successful_html_content", "")
    st.session_state.setdefault("force_proxy_checkbox", False)

    proxy_settings = get_proxy_settings(); proxy_ok = proxy_settings is not None
    if not proxy_ok:
        st.warning("⚠️ Proxy no configurado. El modo 'forzar proxy' y los reintentos con proxy no funcionarán.")

    st.session_state.urls_input = st.text_area(
        "📝 URLs de Booking (una por línea):",
        st.session_state.urls_input, height=150,
        placeholder="Ej: https://www.booking.com/hotel/es/nombre-hotel.es.html"
    )
    st.session_state.force_proxy_checkbox = st.checkbox(
        "Usar proxy directamente (con bloqueo agresivo)", # Texto del checkbox actualizado
        value=st.session_state.force_proxy_checkbox, disabled=(not proxy_ok),
        help="Si se marca, todas las URLs usan proxy y bloqueo agresivo. Si no, se intenta sin proxy (bloqueo ligero) y reintentos con proxy (bloqueo agresivo)."
    )
    st.caption("La optimización de bloqueo de recursos se ajusta según el uso del proxy.")

    col1, col2 = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear con Playwright", use_container_width=True)

    if buscar_btn:
        urls_raw = st.session_state.urls_input.split("\n")
        urls = [url.strip() for url in urls_raw if url.strip() and "booking.com/hotel" in url.strip()]
        if not urls: st.warning("Introduce URLs válidas de Booking.com."); st.stop()

        forzar_proxy_directo = st.session_state.force_proxy_checkbox
        resultados_actuales = []
        st.session_state.last_successful_html_content = "" 

        if forzar_proxy_directo:
            if not proxy_ok:
                st.error("Error: Proxy directo seleccionado pero no configurado."); st.stop()
            with st.spinner(f"Procesando {len(urls)} URLs CON proxy y bloqueo AGRESIVO..."):
                # Llamar a procesar_urls_en_lote con use_proxy=True y block_aggressively=True
                resultados_actuales = asyncio.run(procesar_urls_en_lote(urls, use_proxy=True, block_resources_aggressively=True))
        else: 
            final_results_map = {}
            with st.spinner(f"Paso 1/2: Intentando {len(urls)} URLs SIN proxy (bloqueo LIGERO)..."):
                # Llamar con use_proxy=False y block_aggressively=False
                results_pass_1 = asyncio.run(procesar_urls_en_lote(urls, use_proxy=False, block_resources_aggressively=False))

            urls_a_reintentar = []
            for i, result in enumerate(results_pass_1):
                url_procesada_p1 = urls[i]
                final_results_map[url_procesada_p1] = result
                if isinstance(result, dict) and result.get("error"): urls_a_reintentar.append(url_procesada_p1)
                elif not isinstance(result, dict):
                    urls_a_reintentar.append(url_procesada_p1)
                    final_results_map[url_procesada_p1] = {"error":"Fallo_FormatoInvalidoP1", "url_original":url_procesada_p1, "details":"Resultado no fue dict"}
            
            if urls_a_reintentar:
                st.info(f"{len(urls_a_reintentar)} URL(s) fallaron sin proxy. Preparando reintento CON proxy y bloqueo AGRESIVO...")
                if not proxy_ok:
                    st.error("Proxy no configurado. No se pueden reintentar las URLs fallidas con proxy.")
                else:
                    with st.spinner(f"Paso 2/2: Reintentando {len(urls_a_reintentar)} URL(s) CON proxy y bloqueo AGRESIVO..."):
                        # Llamar con use_proxy=True y block_aggressively=True
                        results_pass_2 = asyncio.run(procesar_urls_en_lote(urls_a_reintentar, use_proxy=True, block_resources_aggressively=True))
                    for i, result_retry in enumerate(results_pass_2):
                        url_retry = urls_a_reintentar[i]
                        if isinstance(result_retry, dict):
                            result_retry["nota"] = "Resultado tras reintento con proxy (Playwright con bloqueo agresivo)"
                            final_results_map[url_retry] = result_retry
                        else:
                            final_results_map[url_retry] = {"error":"Fallo_FormatoInvalidoP2", "url_original":url_retry, "details":"Resultado reintento no fue dict"}
            elif not forzar_proxy_directo:
                st.success("¡Todas las URLs se procesaron con éxito sin necesidad de proxy (con bloqueo ligero)!")
            
            resultados_actuales = [final_results_map[url] for url in urls]

        st.session_state.resultados_finales = resultados_actuales
        st.rerun()

    # ... (Mostrar Resultados y Descarga de HTML se mantienen igual) ...
    if st.session_state.resultados_finales:
        st.markdown("---"); st.subheader("📊 Resultados Finales (Playwright)")
        num_exitos = sum(1 for r in st.session_state.resultados_finales if isinstance(r, dict) and not r.get("error"))
        num_fallos = len(st.session_state.resultados_finales) - num_exitos
        first_successful_result_requests = "N/A"; first_successful_result_blocked = "N/A"; first_successful_result_net = "N/A"
        for r_val in st.session_state.resultados_finales:
            if isinstance(r_val, dict) and not r_val.get("error") and "request_count_total_iniciados" in r_val:
                first_successful_result_requests = r_val["request_count_total_iniciados"]
                first_successful_result_blocked = r_val.get("request_count_bloqueados", "N/A")
                first_successful_result_net = r_val.get("request_count_netos_estimados", "N/A")
                break
        st.write(f"Procesados: {len(st.session_state.resultados_finales)} | Éxitos: {num_exitos} | Fallos: {num_fallos}")
        st.caption(f"Requests (aprox) en el primer éxito: {first_successful_result_net} (Iniciados: {first_successful_result_requests}, Bloqueados: {first_successful_result_blocked})")
        with st.expander("Ver resultados detallados (JSON)", expanded=(num_fallos > 0)):
             st.json(st.session_state.resultados_finales)
    if st.session_state.last_successful_html_content:
        st.markdown("---"); st.subheader("📄 Último HTML Capturado con Éxito")
        try:
            html_bytes = st.session_state.last_successful_html_content.encode("utf-8")
            st.download_button(label="⬇️ Descargar HTML", data=html_bytes,
                file_name="ultimo_hotel_booking_playwright.html", mime="text/html")
        except Exception as e: st.error(f"No se pudo preparar el HTML para descarga: {e}")

# --- Ejecutar ---
if __name__ == "__main__":
    render_scraping_booking()
