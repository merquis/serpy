"""
Servicio de Booking Scraping - Extracción de datos de hoteles
"""
import json
import datetime
import re
from typing import List, Dict, Any, Optional, Union
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import logging
import asyncio
from rebrowser_playwright.async_api import async_playwright
from lxml import html
# import lxml.etree as etree # No se usa etree directamente, html.fromstring es suficiente

logger = logging.getLogger(__name__)

class BookingExtraerDatosService:
    """Servicio para extraer datos de hoteles de Booking.com"""
    
    def __init__(self):
        pass
    
    def extract_urls_from_json(self, json_data: Union[str, dict]) -> List[str]:
        """
        Extrae URLs de un JSON de resultados de búsqueda
        
        Args:
            json_data: JSON string o diccionario con resultados de búsqueda
            
        Returns:
            Lista de URLs con parámetros (url_arg)
        """
        try:
            # Si es string, parsearlo
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            urls = []
            
            # Extraer URLs de la lista de hoteles
            if "hotels" in data and isinstance(data["hotels"], list):
                for hotel in data["hotels"]:
                    # Preferir url_arg que tiene los parámetros de búsqueda
                    if "url_arg" in hotel and hotel["url_arg"]:
                        urls.append(hotel["url_arg"])
                    elif "url" in hotel and hotel["url"]:
                        urls.append(hotel["url"])
            
            return urls
            
        except Exception as e:
            logger.error(f"Error extrayendo URLs del JSON: {e}")
            return []
    
    def parse_urls_input(self, input_text: str) -> List[str]:
        """
        Parsea un texto de entrada para extraer URLs
        Soporta:
        - URLs separadas por saltos de línea
        - URLs separadas por comas
        - JSON con estructura de resultados de búsqueda
        
        Args:
            input_text: Texto con URLs o JSON
            
        Returns:
            Lista de URLs únicas
        """
        urls = []
        
        # Limpiar el texto
        input_text = input_text.strip()
        
        # Verificar si es un JSON
        if input_text.startswith('{') and input_text.endswith('}'):
            try:
                json_urls = self.extract_urls_from_json(input_text)
                urls.extend(json_urls)
                logger.info(f"Extraídas {len(json_urls)} URLs del JSON")
            except Exception as e:
                logger.warning(f"Error parseando JSON: {e}")
                # Si falla el parseo JSON, continuar con el procesamiento normal
                pass
        
        # Si no se encontraron URLs en el JSON o no es JSON, procesar como texto
        if not urls:
            # Reemplazar comas por saltos de línea para unificar el procesamiento
            input_text = input_text.replace(',', '\n')
            
            # Dividir por líneas
            lines = input_text.split('\n')
            
            for line in lines:
                line = line.strip()
                # Buscar URLs en la línea
                if 'booking.com/hotel/' in line:
                    # Extraer URL si está dentro de comillas o como texto plano
                    url_match = re.search(r'https?://[^\s"\']+booking\.com/hotel/[^\s"\']+', line)
                    if url_match:
                        urls.append(url_match.group(0))
                elif line.startswith('http'):
                    urls.append(line)
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_urls = []
        for url_item in urls:
            if url_item not in seen:
                seen.add(url_item)
                unique_urls.append(url_item)
        
        logger.info(f"Total de URLs únicas encontradas: {len(unique_urls)}")
        for i, url_log in enumerate(unique_urls[:3]):
            logger.info(f"URL {i+1}: {url_log}")
        if len(unique_urls) > 3:
            logger.info(f"... y {len(unique_urls) - 3} URLs más")
        
        return unique_urls
    
    def _extract_hotel_name_from_url(self, url: str) -> str:
        """
        Extrae el nombre del hotel de la URL de Booking
        
        Args:
            url: URL del hotel en Booking
            
        Returns:
            Nombre del hotel extraído o "Hotel" si no se puede extraer
        """
        try:
            # Parsear la URL
            parsed = urlparse(url)
            path = parsed.path
            
            # Buscar el segmento que contiene el nombre del hotel
            # Ejemplo: /hotel/es/barcelo-tenerife.es.html
            path_parts = path.split('/')
            
            for part in path_parts:
                # El nombre del hotel suele estar después del código de país
                if part and not part in ['hotel', 'es', 'en', 'fr', 'de', 'it']:
                    # Limpiar el nombre
                    hotel_name = part
                    
                    # Quitar extensiones
                    hotel_name = hotel_name.replace('.es.html', '')
                    hotel_name = hotel_name.replace('.html', '')
                    hotel_name = hotel_name.replace('.htm', '')
                    
                    # Reemplazar guiones por espacios
                    hotel_name = hotel_name.replace('-', ' ')
                    
                    # Capitalizar palabras
                    hotel_name = ' '.join(word.capitalize() for word in hotel_name.split())
                    
                    # Si el nombre es muy corto o parece ser un código, intentar con el siguiente
                    if len(hotel_name) > 3 and not hotel_name.isdigit():
                        return hotel_name
            
            return "Hotel" # Fallback
            
        except Exception as e:
            logger.debug(f"Error extrayendo nombre del hotel de URL {url}: {e}")
            return "Hotel" # Fallback
    
    async def scrape_hotels(
        self,
        urls: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrae datos de múltiples URLs de hoteles en Booking.com
        
        Args:
            urls: Lista de URLs de hoteles
            progress_callback: Función callback para actualizar progreso
            
        Returns:
            Lista de resultados con datos de hoteles
        """
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            try:
                for i, url_item in enumerate(urls):
                    try:
                        # Actualizar progreso
                        if progress_callback:
                            hotel_name_prog = self._extract_hotel_name_from_url(url_item)
                            progress_info = {
                                "message": f"📍 Procesando hotel {i+1}/{len(urls)}: {hotel_name_prog}",
                                "current_url": url_item,
                                "completed": i,
                                "total": len(urls),
                                "remaining": len(urls) - i - 1
                            }
                            progress_callback(progress_info)
                        
                        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                        await page.goto(url_item, wait_until="networkidle", timeout=60000)
                        await page.wait_for_timeout(3000)
                        
                        try:
                            await page.wait_for_selector('[data-hotel-rounded-price]', timeout=5000)
                            logger.info("Encontrado elemento con data-hotel-rounded-price")
                        except:
                            logger.warning("No se encontró elemento con data-hotel-rounded-price en 5 segundos")
                        
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        
                        html_content = await page.content()
                        js_data = await self._extract_javascript_data(page)
                        await page.close()
                        
                        soup = BeautifulSoup(html_content, "html.parser")
                        hotel_data = self._parse_hotel_html(soup, url_item, js_data)
                        # El campo "method" ya no es necesario en la nueva estructura superior,
                        # pero lo mantenemos por si se usa internamente o para logs.
                        # hotel_data["method"] = "rebrowser-playwright" 
                        results.append(hotel_data)
                        
                    except Exception as e:
                        logger.error(f"Error procesando {url_item}: {e}")
                        # Crear una estructura de error que coincida con el formato esperado
                        error_meta = {
                            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "busqueda_checkin": "", "busqueda_checkout": "", "busqueda_adultos": "",
                            "busqueda_ninos": "", "busqueda_habitaciones": "",
                            "nombre_alojamiento": f"Error al procesar URL",
                            "tipo_alojamiento": "hotel", "titulo_h1": "", "subtitulos_h2": [],
                            "slogan_principal": "", "descripcion_corta": f"<p>Error procesando: {str(e)}</p>",
                            "estrellas": "", "precio_noche": "", "alojamiento_destacado": "No",
                            "isla_relacionada": "", "frases_destacadas": {}, "servicios": [],
                            "rango_precios": "", "numero_opiniones": "",
                            "valoracion_limpieza": "", "valoracion_confort": "", "valoracion_ubicacion": "",
                            "valoracion_instalaciones_servicios_": "", "valoracion_personal": "",
                            "valoracion_calidad_precio": "", "valoracion_wifi": "", "valoracion_global": "",
                            "imagenes": [], "direccion": "", "codigo_postal": "", "ciudad": "", "pais": "",
                            "enlace_afiliado": url_item, "sitio_web_oficial": ""
                        }
                        results.append({
                            "title": f"Error procesando URL: {self._extract_hotel_name_from_url(url_item)}",
                            "slug": f"error-procesando-{self._extract_hotel_name_from_url(url_item).lower().replace(' ','-')}",
                            "status": "draft", # Marcar como borrador si hay error
                            "content": f"<p>Ocurrió un error al procesar la información para esta URL: {url_item}. Detalles: {str(e)}</p>",
                            "featured_media": 0, "parent": 0, "template": "",
                            "meta": error_meta
                        })
                
                if progress_callback:
                    progress_info = {
                        "message": f"Completado: {len(urls)} URLs procesadas",
                        "completed": len(urls), "total": len(urls), "remaining": 0
                    }
                    progress_callback(progress_info)
                    
            finally:
                await browser.close()
        
        return results
    
    async def _extract_javascript_data(self, page) -> Dict[str, Any]:
        js_data = {}
        try:
            utag_data = await page.evaluate("() => window.utag_data || {}")
            if utag_data: js_data["utag_data"] = utag_data
            
            data_layer = await page.evaluate("() => window.dataLayer || []")
            if data_layer and len(data_layer) > 0:
                js_data["dataLayer"] = data_layer[0] if isinstance(data_layer, list) else data_layer
            
            formatted_address = await self._search_formatted_address(page)
            if formatted_address: js_data["formattedAddress"] = formatted_address
            
            reviews_count = await self._search_reviews_count(page)
            if reviews_count: js_data["reviewsCount"] = reviews_count
        except Exception as e:
            logger.error(f"Error extrayendo datos de JavaScript: {e}")
        return js_data
    
    async def _search_formatted_address(self, page) -> str:
        try:
            formatted_address = await page.evaluate("""
                () => {
                    function findFormattedAddress(obj, maxDepth = 5, currentDepth = 0) {
                        if (currentDepth > maxDepth || !obj || typeof obj !== 'object') return null;
                        if (obj.formattedAddress && typeof obj.formattedAddress === 'string') return obj.formattedAddress;
                        if (obj.address && obj.address.formattedAddress) return obj.address.formattedAddress;
                        for (let key in obj) {
                            try {
                                if (typeof obj[key] === 'object' && obj[key] !== null) {
                                    const result = findFormattedAddress(obj[key], maxDepth, currentDepth + 1);
                                    if (result) return result;
                                }
                            } catch (e) {}
                        }
                        return null;
                    }
                    const caplaScript = document.querySelector('script[data-capla-application-context]');
                    if (caplaScript && caplaScript.textContent) {
                        try { const caplaData = JSON.parse(caplaScript.textContent); const result = findFormattedAddress(caplaData); if (result) return result; } catch (e) {}
                    }
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (let script of scripts) {
                        try { const data = JSON.parse(script.textContent); const result = findFormattedAddress(data); if (result) return result; } catch (e) {}
                    }
                    const jsonScripts = document.querySelectorAll('script[type="application/json"]');
                    for (let script of jsonScripts) {
                        try { const data = JSON.parse(script.textContent); const result = findFormattedAddress(data); if (result) return result; } catch (e) {}
                    }
                    if (window.__INITIAL_STATE__) { const result = findFormattedAddress(window.__INITIAL_STATE__); if (result) return result; }
                    if (window.b_hotel_data) { const result = findFormattedAddress(window.b_hotel_data); if (result) return result; }
                    for (let key in window) {
                        try { if (typeof window[key] === 'object' && window[key] !== null) { const result = findFormattedAddress(window[key], 3); if (result) return result; } } catch (e) {}
                    }
                    return '';
                }
            """)
            if formatted_address: return formatted_address
            
            address_selectors = ['[data-testid="address"]', '.hp_address_subtitle', '.hp-hotel-address', '.address', '[class*="address"]', '[data-address]']
            for selector in address_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 10: return text.strip()
                except: continue
            return ""
        except Exception as e:
            logger.error(f"Error buscando formattedAddress: {e}")
            return ""

    def _calculate_nights_from_url(self, url: str) -> Optional[int]:
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            checkin_str = query_params.get('checkin', [''])[0]
            checkout_str = query_params.get('checkout', [''])[0]
            if checkin_str and checkout_str:
                checkin_dt = datetime.datetime.strptime(checkin_str, '%Y-%m-%d')
                checkout_dt = datetime.datetime.strptime(checkout_str, '%Y-%m-%d')
                nights = (checkout_dt - checkin_dt).days
                if nights > 0: return nights
        except Exception as e:
            logger.debug(f"Error calculando noches desde URL: {e}")
        return None

    async def _search_reviews_count(self, page) -> str:
        try:
            reviews_count = await page.evaluate("""
                () => {
                    function findReviewsCount(obj, maxDepth = 5, currentDepth = 0) {
                        if (currentDepth > maxDepth || !obj || typeof obj !== 'object') return null;
                        if (obj.reviewsCount !== undefined && obj.reviewsCount !== null) return obj.reviewsCount.toString();
                        for (let key in obj) {
                            try { if (typeof obj[key] === 'object' && obj[key] !== null) { const result = findReviewsCount(obj[key], maxDepth, currentDepth + 1); if (result) return result; } } catch (e) {}
                        }
                        return null;
                    }
                    const allScripts = document.querySelectorAll('script');
                    for (let script of allScripts) {
                        if (script.textContent) {
                            const patterns = [
                                /showReviews:\s*parseInt\s*\(\s*["'](\d+)["']\s*,\s*[^)]+\)/,
                                /showReviews:\s*parseInt\s*\(\s*(\d+)\s*,\s*[^)]+\)/,
                                /showReviews:\s*parseInt\s*\(\s*["'](\d+)["']\s*\)/,
                                /showReviews:\s*parseInt\s*\(\s*(\d+)\s*\)/
                            ];
                            for (let pattern of patterns) { const match = script.textContent.match(pattern); if (match && match[1]) return match[1]; }
                        }
                    }
                    const caplaScript = document.querySelector('script[data-capla-application-context]');
                    if (caplaScript && caplaScript.textContent) {
                        try { const caplaData = JSON.parse(caplaScript.textContent); const result = findReviewsCount(caplaData); if (result) return result; } catch (e) {}
                    }
                    return '';
                }
            """)
            return reviews_count if reviews_count else ""
        except Exception as e:
            logger.error(f"Error buscando reviewsCount: {e}")
            return ""

    def _extract_postal_code_from_address(self, address: str) -> str:
        if not address: return ""
        try:
            postal_5_digits = re.findall(r'\b\d{5}\b', address)
            if postal_5_digits: return postal_5_digits[0]
            postal_4_digits = re.findall(r'\b\d{4}\b', address)
            if postal_4_digits: return postal_4_digits[0]
            return ""
        except Exception as e:
            logger.debug(f"Error extrayendo código postal de '{address}': {e}")
            return ""

    def _calculate_price_per_night(self, price_info: str, nights: Optional[int]) -> str:
        if not price_info or not nights or nights <= 0: return price_info or ""
        try:
            price_match = re.search(r'(\d+(?:[.,]\d+)?)', price_info)
            if price_match:
                price_str = price_match.group(1).replace(',', '.')
                total_price = float(price_str)
                price_per_night = round(total_price / nights, 2)
                return f"{price_per_night} EUR por noche" # Asume EUR, podría mejorarse
            return price_info
        except Exception as e:
            logger.debug(f"Error calculando precio por noche: {e}")
            return price_info or ""

    def _parse_hotel_html(self, soup: BeautifulSoup, url: str, js_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parsea el HTML de la página del hotel y combina con datos de JavaScript para la nueva estructura."""
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        group_adults = query_params.get('group_adults', [''])[0]
        group_children = query_params.get('group_children', [''])[0]
        no_rooms = query_params.get('no_rooms', [''])[0]
        checkin = query_params.get('checkin', [''])[0]
        checkout = query_params.get('checkout', [''])[0]
        
        data_extraida = self._extract_structured_data(soup)
        imagenes_list = self._extract_images(soup)
        servicios_list = self._extract_facilities(soup)
        
        titulo_h1_val = soup.find("h1").get_text(strip=True) if soup.find("h1") else data_extraida.get("name", "")
        h2s_list = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
        
        address_info = data_extraida.get("address", {})
        rating_info = data_extraida.get("aggregateRating", {})
        
        js_utag_data = js_data.get("utag_data", {}) if js_data else {}
        js_data_layer = js_data.get("dataLayer", {}) if js_data else {}
        
        def get_best_value(js_key_utag, js_key_layer, html_value, fallback=""):
            val_utag = js_utag_data.get(js_key_utag)
            if val_utag is not None and val_utag != '': return str(val_utag)
            val_layer = js_data_layer.get(js_key_layer)
            if val_layer is not None and val_layer != '': return str(val_layer)
            if html_value is not None and html_value != '': return str(html_value)
            return fallback

        precio_mas_barato = ""
        try:
            tree = html.fromstring(str(soup))
            xpaths = [
                "//span[contains(@class, 'prco-valign-middle-helper')]/text()",
                "//div[contains(@class, 'bui-price-display__value')]//span[contains(@class, 'prco-valign-middle-helper')]/text()",
                "//div[contains(@data-testid, 'price-and-discounted-price')]//span[contains(@class, 'Value')]/text()", # Nuevo selector más específico
                "//div[@data-testid='property-card-container']//div[@data-testid='price-and-discounted-price']/span[1]/text()", # Para tarjetas
                "//span[@data-testid='price-text']/text()" # Otro común
            ]
            for xpath_expr in xpaths:
                elements = tree.xpath(xpath_expr)
                if elements:
                    raw_price = str(elements[0]).strip()
                    # Limpiar el precio (quitar moneda, espacios, etc.)
                    cleaned_price = re.sub(r'[^\d,.]', '', raw_price).replace(',', '.')
                    if cleaned_price:
                        precio_mas_barato = cleaned_price
                        logger.info(f"Precio extraído con XPath '{xpath_expr}': {precio_mas_barato} (raw: {raw_price})")
                        break
            if not precio_mas_barato: logger.warning(f"No se encontró el elemento del precio para {url}")
        except Exception as e: logger.error(f"Error usando XPath para precio en {url}: {e}")

        nombre_alojamiento_val = get_best_value("hotel_name", "hotel_name", data_extraida.get("name", titulo_h1_val))
        ciudad_val = get_best_value("city_name", "city_name", address_info.get("addressLocality"))
        
        title_str = f"{nombre_alojamiento_val} – Lujo exclusivo en {ciudad_val}" if nombre_alojamiento_val and ciudad_val else nombre_alojamiento_val or "Alojamiento sin título"
        
        def generate_slug_simple(text: str) -> str:
            if not text: return "alojamiento-sin-slug"
            s = text.lower()
            s = re.sub(r'[^\w\s-]', '', s)
            s = re.sub(r'\s+', '-', s)
            s = re.sub(r'-+', '-', s)
            return s.strip('-') or "slug"

        slug_str = generate_slug_simple(title_str)
        descripcion_corta_raw = data_extraida.get("description", "")
        descripcion_corta_html = f"<p>{descripcion_corta_raw}</p>" if descripcion_corta_raw else "<p></p>"
        content_html = f"<p>{nombre_alojamiento_val} es un alojamiento destacado en {ciudad_val}. {descripcion_corta_raw}</p>" if nombre_alojamiento_val and ciudad_val else descripcion_corta_html

        meta_data = {
            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "busqueda_checkin": checkin or "",
            "busqueda_checkout": checkout or "",
            "busqueda_adultos": group_adults or "",
            "busqueda_ninos": group_children or "",
            "busqueda_habitaciones": no_rooms or "",
            "nombre_alojamiento": nombre_alojamiento_val or "",
            "tipo_alojamiento": get_best_value("hotel_type", "hotel_type", data_extraida.get("@type", "hotel"), "hotel").lower(),
            "titulo_h1": titulo_h1_val or "",
            "subtitulos_h2": h2s_list or [],
            "slogan_principal": "",
            "descripcion_corta": descripcion_corta_html,
            "estrellas": get_best_value("hotel_class", "hotel_class", data_extraida.get("starRating", {}).get("ratingValue", "")) or "",
            "precio_noche": precio_mas_barato or "", # Usar el precio extraído
            "alojamiento_destacado": "No",
            "isla_relacionada": "",
            "frases_destacadas": {},
            "servicios": servicios_list or [],
            "rango_precios": f"{precio_mas_barato} EUR" if precio_mas_barato else "", # Formatear rango_precios
            "numero_opiniones": get_best_value("reviewCount", "reviewCount", rating_info.get("reviewCount")) or "",
            "valoracion_limpieza": "", "valoracion_confort": "", "valoracion_ubicacion": "",
            "valoracion_instalaciones_servicios_": "", "valoracion_personal": "",
            "valoracion_calidad_precio": "", "valoracion_wifi": "",
            "valoracion_global": get_best_value("utrs", "utrs", rating_info.get("ratingValue")) or "",
            "imagenes": imagenes_list or [],
            "direccion": get_best_value("formattedAddress", "formattedAddress", address_info.get("streetAddress")) or "",
            "codigo_postal": self._extract_postal_code_from_address(get_best_value("formattedAddress", "formattedAddress", address_info.get("streetAddress"))) or address_info.get("postalCode", ""),
            "ciudad": ciudad_val or "",
            "pais": get_best_value("country_name", "country_name", address_info.get("addressCountry")) or "",
            "enlace_afiliado": url or "",
            "sitio_web_oficial": ""
        }

        final_output = {
            "title": title_str,
            "slug": slug_str,
            "status": "publish",
            "content": content_html,
            "featured_media": 0,
            "parent": 0,
            "template": "",
            "meta": meta_data
        }
        return final_output

    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae datos estructurados JSON-LD"""
        try:
            scripts_ldjson = soup.find_all('script', type='application/ld+json')
            for script in scripts_ldjson:
                if script.string:
                    try:
                        data_json = json.loads(script.string)
                        # Buscar Hotel o LodgingBusiness que es más genérico
                        type_val = data_json.get("@type")
                        if isinstance(type_val, list): # A veces @type es una lista
                            if "Hotel" in type_val or "LodgingBusiness" in type_val:
                                return data_json
                        elif type_val in ["Hotel", "LodgingBusiness"]:
                            return data_json
                    except json.JSONDecodeError:
                        logger.debug(f"Error decodificando JSON-LD: {script.string[:100]}...")
                        continue
        except Exception as e:
            logger.error(f"Error extrayendo datos estructurados: {e}")
        return {}

    def _extract_images(self, soup: BeautifulSoup, max_images: int = 15) -> List[str]:
        """Extrae URLs de imágenes del hotel"""
        imagenes = []
        found_urls = set()
        try:
            # Priorizar imágenes de alta resolución de galerías
            gallery_selectors = [
                'a[data-fancybox="gallery"] img', # Fancybox
                '.bh-photo-grid-item img',        # Booking hotel gallery
                'img[data-src*="xdata/images/hotel"]' # Imágenes de datos
            ]
            for selector in gallery_selectors:
                for img_tag in soup.select(selector):
                    src = img_tag.get("src") or img_tag.get("data-src")
                    if src and src.startswith("https://cf.bstatic.com/xdata/images/hotel/") and ".jpg" in src and src not in found_urls:
                        src = re.sub(r"/max\d+x\d+/", "/max1024x768/", src)
                        src = src.split("?")[0] # Quitar query params
                        if src not in found_urls:
                             imagenes.append(src)
                             found_urls.add(src)
                             if len(imagenes) >= max_images: break
                if len(imagenes) >= max_images: break
            
            # Fallback a todas las imágenes si no se encuentran suficientes
            if len(imagenes) < max_images:
                for img_tag in soup.find_all("img"):
                    src = img_tag.get("src") or img_tag.get("data-lazy") or img_tag.get("data-src")
                    if src and "bstatic.com/xdata/images/hotel" in src and ".jpg" in src and src not in found_urls:
                        src = re.sub(r"/max\d+x\d+/", "/max1024x768/", src)
                        src = src.split("?")[0]
                        if src not in found_urls:
                            imagenes.append(src)
                            found_urls.add(src)
                            if len(imagenes) >= max_images: break
        except Exception as e:
            logger.error(f"Error extrayendo imágenes: {e}")
        return imagenes[:max_images]

    def _extract_facilities(self, soup: BeautifulSoup) -> List[str]:
        """Extrae los servicios/facilidades del hotel"""
        servicios_set = set()
        try:
            # Selectores más específicos y comunes
            selectors = [
                '.hotel-facilities__list li .bui-list__description', # Estructura común
                '.facilitiesChecklistSection li span',              # Otra estructura
                '.hp_desc_important_facilities li',                 # Antigua estructura
                'div[data-testid="property-most-popular-facilities-wrapper"] div[data-testid="facility-badge"] span', # Nueva estructura TestID
                'div[data-testid="facilities-block"] li div:nth-child(2) span' # Otra con TestID
            ]
            for selector in selectors:
                elements = soup.select(selector)
                for item in elements:
                    texto = item.get_text(strip=True)
                    if texto and len(texto) > 2 and len(texto) < 50: # Filtrar textos muy cortos o largos
                        servicios_set.add(texto)

            # Fallback a clases más genéricas si no se encuentran suficientes
            if not servicios_set:
                possible_classes = ["bui-list__description", "db29ecfbe2", "facility_name"]
                for class_name in possible_classes:
                    for container in soup.find_all(class_=class_name):
                        texto = container.get_text(strip=True)
                        if texto and len(texto) > 2 and len(texto) < 50:
                             servicios_set.add(texto)
        except Exception as e:
            logger.error(f"Error extrayendo servicios: {e}")
        return sorted(list(servicios_set))
