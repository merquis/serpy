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
import requests # Añadido para notify_n8n_webhook
from config import settings # Añadido para notify_n8n_webhook
from typing import List, Any, Dict # Asegurarse de que List, Any, Dict estén importados

logger = logging.getLogger(__name__)

# Constantes para scripts JS evaluados en Playwright para mejorar legibilidad
JS_SEARCH_FORMATTED_ADDRESS = """
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
"""

JS_SEARCH_REVIEWS_COUNT = """
    () => {
        function findReviewsCount(obj, maxDepth = 5, currentDepth = 0) {
            if (currentDepth > maxDepth || !obj || typeof obj !== 'object') return null;
            if (obj.reviewsCount !== undefined && obj.reviewsCount !== null) return obj.reviewsCount.toString();
            if (obj.reviewCount !== undefined && obj.reviewCount !== null) return obj.reviewCount.toString(); // Otra posible clave
            if (obj.aggregateRating && obj.aggregateRating.reviewCount !== undefined) return obj.aggregateRating.reviewCount.toString();
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
                    /showReviews:\s*parseInt\s*\(\s*(\d+)\s*\)/,
                    /"reviewCount":\s*"?(\d+)"?/,
                    /"reviewsCount":\s*"?(\d+)"?/
                ];
                for (let pattern of patterns) { const match = script.textContent.match(pattern); if (match && match[1]) return match[1]; }
            }
        }
        const caplaScript = document.querySelector('script[data-capla-application-context]');
        if (caplaScript && caplaScript.textContent) {
            try { const caplaData = JSON.parse(caplaScript.textContent); const result = findReviewsCount(caplaData); if (result) return result; } catch (e) {}
        }
        // Buscar en dataLayer y utag_data
        if (window.dataLayer) { for(let item of window.dataLayer) { const result = findReviewsCount(item); if (result) return result; } }
        if (window.utag_data) { const result = findReviewsCount(window.utag_data); if (result) return result; }
        return '';
    }
"""

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
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            urls = []
            
            if "hotels" in data and isinstance(data["hotels"], list):
                for hotel in data["hotels"]:
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
        input_text = input_text.strip()
        
        if input_text.startswith('{') and input_text.endswith('}'):
            try:
                json_urls = self.extract_urls_from_json(input_text)
                urls.extend(json_urls)
                logger.info(f"Extraídas {len(json_urls)} URLs del JSON")
            except Exception as e:
                logger.warning(f"Error parseando JSON: {e}")
        
        if not urls:
            input_text = input_text.replace(',', '\n')
            lines = input_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if 'booking.com/hotel/' in line:
                    url_match = re.search(r'https?://[^\s"\']+booking\.com/hotel/[^\s"\']+', line)
                    if url_match:
                        urls.append(url_match.group(0))
                elif line.startswith('http'):
                    urls.append(line)
        
        seen = set()
        unique_urls = [x for x in urls if not (x in seen or seen.add(x))]
        
        logger.info(f"Total de URLs únicas encontradas: {len(unique_urls)}")
        for i, url_log in enumerate(unique_urls[:3]):
            logger.info(f"URL {i+1}: {url_log}")
        if len(unique_urls) > 3:
            logger.info(f"... y {len(unique_urls) - 3} URLs más")
        
        return unique_urls
    
    def _extract_hotel_name_from_url(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            path = parsed.path
            path_parts = path.split('/')
            
            for part in path_parts:
                if part and not part in ['hotel', 'es', 'en', 'fr', 'de', 'it']:
                    hotel_name = part.replace('.es.html', '').replace('.html', '').replace('.htm', '').replace('-', ' ')
                    hotel_name = ' '.join(word.capitalize() for word in hotel_name.split())
                    if len(hotel_name) > 3 and not hotel_name.isdigit():
                        return hotel_name
            return "Hotel"
        except Exception as e:
            logger.debug(f"Error extrayendo nombre del hotel de URL {url}: {e}")
            return "Hotel"

    def _generate_error_response(self, url: str, error_message: str) -> Dict[str, Any]:
        hotel_name_from_url = self._extract_hotel_name_from_url(url)
        error_meta = {
            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "busqueda_checkin": "", "busqueda_checkout": "", "busqueda_adultos": "",
            "busqueda_ninos": "", "busqueda_habitaciones": "",
            "nombre_alojamiento": f"Error al procesar: {hotel_name_from_url}",
            "tipo_alojamiento": "hotel", "titulo_h1": "", "subtitulos_h2": [],
            "slogan_principal": "", "descripcion_corta": f"<p>Error procesando URL: {error_message}</p>",
            "estrellas": "", "precio_noche": "", "alojamiento_destacado": "No",
            "isla_relacionada": "", "frases_destacadas": {}, "servicios": [],
            "rango_precios": "", "numero_opiniones": "",
            "valoracion_limpieza": "", "valoracion_confort": "", "valoracion_ubicacion": "",
            "valoracion_instalaciones_servicios_": "", "valoracion_personal": "",
            "valoracion_calidad_precio": "", "valoracion_wifi": "", "valoracion_global": "",
            "imagenes": [], "direccion": "", "codigo_postal": "", "ciudad": "", "pais": "",
            "enlace_afiliado": url, "sitio_web_oficial": ""
        }
        return {
            "title": f"Error procesando: {hotel_name_from_url}",
            "slug": f"error-procesando-{hotel_name_from_url.lower().replace(' ','-').replace('/','-')}",
            "status": "draft",
            "content": f"<p>Ocurrió un error al procesar la información para la URL: {url}.<br>Detalles: {error_message}</p>",
            "featured_media": 0, "parent": 0, "template": "",
            "meta": error_meta
        }

    async def scrape_hotels(
        self,
        urls: List[str],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            try:
                for i, url_item in enumerate(urls):
                    try:
                        if progress_callback:
                            hotel_name_prog = self._extract_hotel_name_from_url(url_item)
                            progress_info = {
                                "message": f"📍 Procesando hotel {i+1}/{len(urls)}: {hotel_name_prog}",
                                "current_url": url_item, "completed": i, "total": len(urls),
                                "remaining": len(urls) - i - 1
                            }
                            progress_callback(progress_info)
                        
                        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                        await page.goto(url_item, wait_until="networkidle", timeout=60000)
                        await page.wait_for_timeout(2000)
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1500)
                        
                        html_content = await page.content()
                        js_data = await self._extract_javascript_data(page)
                        await page.close()
                        
                        soup = BeautifulSoup(html_content, "html.parser")
                        hotel_data = self._parse_hotel_html(soup, url_item, js_data)
                        results.append(hotel_data)
                    except Exception as e:
                        logger.error(f"Error procesando {url_item}: {e}")
                        results.append(self._generate_error_response(url_item, str(e)))
                
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
        js_data_extracted = {}
        try:
            js_data_extracted["utag_data"] = await page.evaluate("() => window.utag_data || {}")
            data_layer_raw = await page.evaluate("() => window.dataLayer || []")
            if data_layer_raw:
                js_data_extracted["dataLayer"] = data_layer_raw[0] if isinstance(data_layer_raw, list) and data_layer_raw else data_layer_raw
            js_data_extracted["formattedAddress"] = await self._search_formatted_address(page)
            js_data_extracted["reviewsCount"] = await self._search_reviews_count(page)
            return {k: v for k, v in js_data_extracted.items() if v}
        except Exception as e:
            logger.error(f"Error extrayendo datos de JavaScript: {e}")
        return {}
    
    async def _search_formatted_address(self, page) -> str:
        try:
            formatted_address = await page.evaluate(JS_SEARCH_FORMATTED_ADDRESS)
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
            reviews_count = await page.evaluate(JS_SEARCH_REVIEWS_COUNT)
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

    def _generate_slug(self, text: str) -> str:
        if not text: return "alojamiento-sin-slug"
        s = text.lower()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'\s+', '-', s)
        s = re.sub(r'-+', '-', s)
        return s.strip('-') or "slug"

    def _parse_hotel_html(self, soup: BeautifulSoup, url: str, js_data: Dict[str, Any] = None) -> Dict[str, Any]:
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
        
        titulo_h1_val = soup.find("h2", class_="pp-header__title").get_text(strip=True) if soup.find("h2", class_="pp-header__title") else \
                        (soup.find("h1", {"id": "hp_hotel_name"}).get_text(strip=True).replace("¡Reserva ya!", "").strip() if soup.find("h1", {"id": "hp_hotel_name"}) else data_extraida.get("name", ""))

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
        tree = html.fromstring(str(soup))
        try:
            xpaths = [
                "//span[contains(@class, 'prco-valign-middle-helper')]/text()",
                "//div[contains(@class, 'bui-price-display__value')]//span[contains(@class, 'prco-valign-middle-helper')]/text()",
                "//div[contains(@data-testid, 'price-and-discounted-price')]//span[contains(@class, 'Value')]/text()",
                "//div[@data-testid='property-card-container']//div[@data-testid='price-and-discounted-price']/span[1]/text()",
                "//span[@data-testid='price-text']/text()"
            ]
            for xpath_expr in xpaths:
                elements = tree.xpath(xpath_expr)
                if elements:
                    raw_price = str(elements[0]).strip()
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
        slug_str = self._generate_slug(title_str)
        
        descripcion_corta_raw = data_extraida.get("description", "")
        if not descripcion_corta_raw:
            desc_tag = soup.find("meta", {"name": "description"})
            if desc_tag and desc_tag.get("content"):
                descripcion_corta_raw = desc_tag.get("content")
        
        descripcion_corta_html = f"<p>{descripcion_corta_raw}</p>" if descripcion_corta_raw else "<p></p>"
        content_html = f"<p>{nombre_alojamiento_val} es un alojamiento destacado en {ciudad_val}. {descripcion_corta_raw}</p>" if nombre_alojamiento_val and ciudad_val else descripcion_corta_html

        meta_data = {
            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "busqueda_checkin": checkin or "", "busqueda_checkout": checkout or "",
            "busqueda_adultos": group_adults or "", "busqueda_ninos": group_children or "",
            "busqueda_habitaciones": no_rooms or "",
            "nombre_alojamiento": nombre_alojamiento_val or "",
            "tipo_alojamiento": get_best_value("hotel_type", "hotel_type", data_extraida.get("@type", "hotel"), "hotel").lower(),
            "titulo_h1": titulo_h1_val or "", "subtitulos_h2": h2s_list or [],
            "slogan_principal": "",
            "descripcion_corta": descripcion_corta_html,
            "estrellas": get_best_value("hotel_class", "hotel_class", data_extraida.get("starRating", {}).get("ratingValue", "")) or "",
            "precio_noche": precio_mas_barato or "",
            "alojamiento_destacado": "No", "isla_relacionada": "",
            "frases_destacadas": {}, "servicios": servicios_list or [],
            "rango_precios": f"{precio_mas_barato} EUR" if precio_mas_barato else "",
            "numero_opiniones": "", "valoracion_limpieza": "", "valoracion_confort": "",
            "valoracion_ubicacion": "", "valoracion_instalaciones_servicios_": "",
            "valoracion_personal": "", "valoracion_calidad_precio": "", "valoracion_wifi": "",
            "valoracion_global": "",
            "imagenes": imagenes_list or [],
            "direccion": get_best_value("formattedAddress", "formattedAddress", address_info.get("streetAddress")) or "",
            "codigo_postal": self._extract_postal_code_from_address(get_best_value("formattedAddress", "formattedAddress", address_info.get("streetAddress"))) or address_info.get("postalCode", ""),
            "ciudad": ciudad_val or "",
            "pais": get_best_value("country_name", "country_name", address_info.get("addressCountry")) or "",
            "enlace_afiliado": url or "", "sitio_web_oficial": ""
        }

        # Nuevas extracciones con XPath
        try:
            es_preferente_elements = tree.xpath('//span[@data-testid="preferred-icon"]')
            meta_data["alojamiento_destacado"] = "Preferente" if es_preferente_elements else "No"
        except Exception as e:
            logger.debug(f"Error extrayendo alojamiento_destacado: {e}")

        try:
            keywords_content_list = tree.xpath('//meta[@name="keywords"]/@content')
            if keywords_content_list:
                keywords_content = keywords_content_list[0]
                match = re.search(r'I:([^,]+)', keywords_content)
                if match:
                    meta_data["isla_relacionada"] = match.group(1).strip()
        except Exception as e:
            logger.debug(f"Error extrayendo isla_relacionada: {e}")

        try:
            review_subscores_elements = tree.xpath('//div[@data-testid="PropertyReviewSubscoresPanel"]//div[@data-testid="review-subscore"]')
            if not review_subscores_elements:
                review_subscores_elements = tree.xpath('//ul[@id="review_list_score_breakdown"]/li')

            for item_element in review_subscores_elements:
                category_name_elements = item_element.xpath('.//div[contains(@class, "d96a4619c0")]/text()')
                score_elements = item_element.xpath('.//div[contains(@class, "f87e152973")]/text()')

                if not category_name_elements or not score_elements:
                    category_name_elements = item_element.xpath('.//p[contains(@class, "review_score_name")]/text()')
                    score_elements = item_element.xpath('.//p[contains(@class, "review_score_value")]/text()')
                
                if category_name_elements and score_elements:
                    category_name_raw = category_name_elements[0].strip().lower()
                    score_value = score_elements[0].strip().replace(",", ".")
                    
                    if "personal" in category_name_raw: meta_data["valoracion_personal"] = score_value
                    elif "instalaciones y servicios" in category_name_raw or "instalaciones_servicios" in category_name_raw: meta_data["valoracion_instalaciones_servicios_"] = score_value
                    elif "limpieza" in category_name_raw: meta_data["valoracion_limpieza"] = score_value
                    elif "confort" in category_name_raw: meta_data["valoracion_confort"] = score_value
                    elif "ubicación" in category_name_raw or "ubicacion" in category_name_raw: meta_data["valoracion_ubicacion"] = score_value
                    elif "calidad-precio" in category_name_raw or "calidad_precio" in category_name_raw: meta_data["valoracion_calidad_precio"] = score_value
                    elif "wifi gratis" in category_name_raw or ("wifi" in category_name_raw and "gratis" in category_name_raw): meta_data["valoracion_wifi"] = score_value
        except Exception as e:
            logger.error(f"Error extrayendo valoraciones detalladas para {url}: {e}")

        if not meta_data.get("numero_opiniones"):
            try:
                num_opiniones_text_elements = tree.xpath('//div[@data-testid="review-score-right-component"]//div[contains(@class, "fb14de7f14")]/text()')
                if num_opiniones_text_elements:
                    match = re.search(r'([\d\.,]+)', num_opiniones_text_elements[0])
                    if match: meta_data["numero_opiniones"] = match.group(1).replace('.', '').replace(',', '')
            except Exception as e: logger.debug(f"Error extrayendo numero_opiniones con XPath: {e}")
        
        if not meta_data.get("valoracion_global"):
            try:
                valoracion_global_elements = tree.xpath('//div[@data-testid="review-score-right-component"]//div[contains(@class, "dff2e52086")]/text()')
                if valoracion_global_elements: meta_data["valoracion_global"] = valoracion_global_elements[0].strip().replace(",", ".")
            except Exception as e: logger.debug(f"Error extrayendo valoracion_global con XPath: {e}")

        frases_destacadas_list = []
        try:
            highlight_elements = tree.xpath('//div[@data-testid="PropertyHighlightList-wrapper"]//ul/li//div[contains(@class, "b99b6ef58f")]//span[contains(@class, "f6b6d2a959")]/text()')
            if not highlight_elements:
                 highlight_elements = tree.xpath('//div[contains(@class, "hp--desc_highlights")]//div[contains(@class,"ph-item-copy-container")]//span/text()')

            for el_text in highlight_elements:
                frase = el_text.strip()
                if frase and len(frase) > 5: frases_destacadas_list.append(frase)
            meta_data["frases_destacadas"] = frases_destacadas_list if frases_destacadas_list else {}
        except Exception as e:
            logger.error(f"Error extrayendo frases destacadas para {url}: {e}")
            meta_data["frases_destacadas"] = {}

        final_output = {
            "title": title_str, "slug": slug_str, "status": "publish",
            "content": content_html, "featured_media": 0, "parent": 0,
            "template": "", "meta": meta_data
        }
        return final_output

    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        try:
            scripts_ldjson = soup.find_all('script', type='application/ld+json')
            for script in scripts_ldjson:
                if script.string:
                    try:
                        data_json = json.loads(script.string)
                        type_val = data_json.get("@type")
                        if isinstance(type_val, list):
                            if "Hotel" in type_val or "LodgingBusiness" in type_val: return data_json
                        elif type_val in ["Hotel", "LodgingBusiness"]: return data_json
                    except json.JSONDecodeError:
                        logger.debug(f"Error decodificando JSON-LD: {script.string[:100]}...")
                        continue
        except Exception as e:
            logger.error(f"Error extrayendo datos estructurados: {e}")
        return {}

    def _extract_images(self, soup: BeautifulSoup, max_images: int = 15) -> List[str]:
        imagenes = []
        found_urls = set()
        try:
            gallery_selectors = [
                'a[data-fancybox="gallery"] img', '.bh-photo-grid-item img',
                'img[data-src*="xdata/images/hotel"]'
            ]
            for selector in gallery_selectors:
                for img_tag in soup.select(selector):
                    src = img_tag.get("src") or img_tag.get("data-src")
                    if src and src.startswith("https://cf.bstatic.com/xdata/images/hotel/") and ".jpg" in src and src not in found_urls:
                        src = re.sub(r"/max\d+x\d+/", "/max1024x768/", src).split("?")[0]
                        if src not in found_urls:
                             imagenes.append(src)
                             found_urls.add(src)
                             if len(imagenes) >= max_images: break
                if len(imagenes) >= max_images: break
            
            if len(imagenes) < max_images:
                for img_tag in soup.find_all("img"):
                    src = img_tag.get("src") or img_tag.get("data-lazy") or img_tag.get("data-src")
                    if src and "bstatic.com/xdata/images/hotel" in src and ".jpg" in src and src not in found_urls:
                        src = re.sub(r"/max\d+x\d+/", "/max1024x768/", src).split("?")[0]
                        if src not in found_urls:
                            imagenes.append(src)
                            found_urls.add(src)
                            if len(imagenes) >= max_images: break
        except Exception as e:
            logger.error(f"Error extrayendo imágenes: {e}")
        return imagenes[:max_images]

    def _extract_facilities(self, soup: BeautifulSoup) -> List[str]:
        servicios_set = set()
        try:
            selectors = [
                '.hotel-facilities__list li .bui-list__description', '.facilitiesChecklistSection li span',
                '.hp_desc_important_facilities li',
                'div[data-testid="property-most-popular-facilities-wrapper"] div[data-testid="facility-badge"] span',
                'div[data-testid="facilities-block"] li div:nth-child(2) span'
            ]
            for selector in selectors:
                elements = soup.select(selector)
                for item in elements:
                    texto = item.get_text(strip=True)
                    if texto and len(texto) > 2 and len(texto) < 50:
                        servicios_set.add(texto)
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

    def notify_n8n_webhook(self, ids: List[Any]) -> Dict[str, Any]:
        """
        Notifica a un webhook de n8n con una lista de IDs.

        Args:
            ids: Lista de IDs a enviar.

        Returns:
            Un diccionario con el estado de la operación:
            {"success": True/False, "message": "Mensaje descriptivo"}
        """
        if not ids:
            logger.warning("No IDs provided to send to n8n.")
            return {"success": False, "message": "No IDs proporcionados para enviar a n8n."}
        try:
            n8n_url = settings.N8N_WEBHOOK_URL
            if not n8n_url:
                logger.warning("La URL del webhook de n8n no está configurada.")
                return {"success": False, "message": "La URL del webhook de n8n no está configurada."}
            
            data_to_send = [{"_id": str(mongo_id)} for mongo_id in ids]
            response = requests.post(n8n_url, json=data_to_send, timeout=10)
            response.raise_for_status()
            
            success_message = f"✅ {len(ids)} IDs enviados a n8n."
            logger.info(f"{success_message} Datos: {data_to_send}")
            return {"success": True, "message": success_message}
        
        except requests.exceptions.RequestException as e:
            error_message = f"❌ Error de red al enviar IDs a n8n: {e}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
        except Exception as e:
            error_message = f"❌ Error inesperado al enviar IDs a n8n: {e}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
