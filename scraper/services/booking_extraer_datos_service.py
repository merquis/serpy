"""
Servicio de Booking Scraping - Extracción de datos de hoteles (Refactorizado)
"""
import json
import datetime
import re
from typing import List, Dict, Any, Optional, Union
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import logging
import asyncio
from rebrowser_playwright.async_api import async_playwright
from lxml import html
from config.settings import settings
from services.utils.httpx_service import httpx_requests

logger = logging.getLogger(__name__)

class XPathExtractor:
    """Clase centralizada para gestionar todos los xpath de extracción"""
    
    # Xpath para información básica del hotel
    HOTEL_NAME = [
        "//h2[contains(@class, 'pp-header__title')]/text()",
        "//h1[@id='hp_hotel_name']/text()",
        "//h1[contains(@class, 'hotel-name')]/text()"
    ]
    
    # Xpath para precios
    PRICE = [
        "//span[contains(@class, 'prco-valign-middle-helper')]/text()",
        "//div[contains(@class, 'bui-price-display__value')]//span[contains(@class, 'prco-valign-middle-helper')]/text()",
        "//div[contains(@data-testid, 'price-and-discounted-price')]//span[contains(@class, 'Value')]/text()",
        "//div[@data-testid='property-card-container']//div[@data-testid='price-and-discounted-price']/span[1]/text()",
        "//span[@data-testid='price-text']/text()"
    ]
    
    # Xpath para valoraciones globales
    GLOBAL_RATING = [
        "//div[@data-testid='review-score-right-component']//div[contains(@class, 'dff2e52086')]/text()",
        "//div[contains(@class, 'bui-review-score__badge')]/text()",
        "//span[contains(@class, 'review-score-badge')]/text()"
    ]
    
    # Xpath para número de opiniones
    REVIEWS_COUNT = [
        "//div[@data-testid='review-score-right-component']//div[contains(@class, 'fb14de7f14')]/text()",
        "//div[contains(@class, 'bui-review-score__text')]/text()",
        "//span[contains(@class, 'review-count')]/text()"
    ]
    
    # Xpath para dirección
    ADDRESS = [
        "//span[@data-testid='address']/text()",
        "//div[contains(@class, 'hp_address_subtitle')]/text()",
        "//div[contains(@class, 'hp-hotel-address')]/text()",
        "//div[contains(@class, 'address')]/text()"
    ]
    
    # Xpath para alojamiento destacado/preferente
    PREFERRED_STATUS = [
        "//span[@data-testid='preferred-icon']",
        "//div[contains(@class, 'preferred-badge')]",
        "//span[contains(@class, 'preferred')]"
    ]
    
    # Xpath para frases destacadas
    HIGHLIGHTS = [
        "//div[@data-testid='PropertyHighlightList-wrapper']//ul/li//div[contains(@class, 'b99b6ef58f')]//span[contains(@class, 'f6b6d2a959')]/text()",
        "//div[contains(@class, 'hp--desc_highlights')]//div[contains(@class,'ph-item-copy-container')]//span/text()",
        "//div[contains(@class, 'property-highlights')]//span/text()"
    ]
    
    # Xpath para servicios/instalaciones
    FACILITIES = [
        "//div[contains(@class, 'hotel-facilities__list')] li .bui-list__description/text()",
        "//div[contains(@class, 'facilitiesChecklistSection')] li span/text()",
        "//div[contains(@class, 'hp_desc_important_facilities')] li/text()",
        "//div[@data-testid='property-most-popular-facilities-wrapper'] div[@data-testid='facility-badge'] span/text()",
        "//div[@data-testid='facilities-block'] li div[2] span/text()"
    ]
    
    # Xpath para imágenes
    IMAGES = [
        "//a[@data-fancybox='gallery'] img",
        "//div[contains(@class, 'bh-photo-grid-item')] img",
        "//img[contains(@data-src, 'xdata/images/hotel')]",
        "//img[contains(@src, 'bstatic.com/xdata/images/hotel')]"
    ]
    
    # Xpath para imagen destacada (imagen principal del hotel)
    FEATURED_IMAGE = [
        "//div[contains(@class, 'hotel-header-image')]//img/@src",
        "//div[contains(@class, 'hotel-header-image')]//img/@data-src",
        "//div[@data-testid='property-gallery']//img[1]/@src",
        "//div[@data-testid='property-gallery']//img[1]/@data-src",
        "//div[contains(@class, 'gallery-container')]//img[1]/@src",
        "//div[contains(@class, 'gallery-container')]//img[1]/@data-src",
        "//img[contains(@src, 'bstatic.com/xdata/images/hotel') and contains(@src, 'max1024x768')][1]/@src",
        "//img[contains(@data-src, 'bstatic.com/xdata/images/hotel') and contains(@data-src, 'max1024x768')][1]/@data-src",
        "//img[contains(@src, 'bstatic.com/xdata/images/hotel')][1]/@src",
        "//img[contains(@data-src, 'bstatic.com/xdata/images/hotel')][1]/@data-src"
    ]
    
    # Xpath para valoraciones detalladas (nuevo sistema unificado)
    DETAILED_RATINGS = {
        'personal': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and (contains(translate(text(), 'PERSONAL', 'personal'), 'personal') or contains(translate(text(), 'STAFF', 'staff'), 'staff'))]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and (contains(translate(text(), 'PERSONAL', 'personal'), 'personal') or contains(translate(text(), 'STAFF', 'staff'), 'staff'))]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'limpieza': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(text(), 'LIMPIEZA', 'limpieza'), 'limpieza')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(translate(text(), 'LIMPIEZA', 'limpieza'), 'limpieza')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'confort': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(translate(text(), 'CONFORT', 'confort'), 'confort')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(translate(text(), 'CONFORT', 'confort'), 'confort')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'ubicacion': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and (contains(translate(text(), 'UBICACIÓN', 'ubicacion'), 'ubicacion') or contains(translate(text(), 'UBICACION', 'ubicacion'), 'ubicacion'))]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and (contains(translate(text(), 'UBICACIÓN', 'ubicacion'), 'ubicacion') or contains(translate(text(), 'UBICACION', 'ubicacion'), 'ubicacion'))]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'instalaciones_servicios': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(text(), 'instalaciones')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(text(), 'instalaciones')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'calidad_precio': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(text(), 'calidad')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(text(), 'calidad')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ],
        'wifi': [
            "//div[@data-testid='review-subscore']//span[contains(@class, 'd96a4619c0') and contains(text(), 'wifi')]/following-sibling::*//div[contains(@class, 'f87e152973')]/text()",
            "//li//p[contains(@class, 'review_score_name') and contains(text(), 'wifi')]/following-sibling::p[contains(@class, 'review_score_value')]/text()"
        ]
    }

class DataExtractor:
    """Clase para extraer datos usando xpath de forma optimizada"""
    
    def __init__(self, tree):
        self.tree = tree
    
    def extract_first_match(self, xpath_list: List[str]) -> str:
        """Extrae el primer resultado encontrado de una lista de xpath"""
        for xpath in xpath_list:
            try:
                elements = self.tree.xpath(xpath)
                if elements:
                    result = str(elements[0]).strip()
                    if result:
                        return result
            except Exception as e:
                logger.debug(f"Error en xpath {xpath}: {e}")
        return ""
    
    def extract_all_matches(self, xpath_list: List[str]) -> List[str]:
        """Extrae todos los resultados encontrados de una lista de xpath"""
        results = []
        for xpath in xpath_list:
            try:
                elements = self.tree.xpath(xpath)
                for element in elements:
                    text = str(element).strip() if hasattr(element, 'strip') else element.get_text(strip=True) if hasattr(element, 'get_text') else str(element).strip()
                    if text and text not in results:
                        results.append(text)
            except Exception as e:
                logger.debug(f"Error en xpath {xpath}: {e}")
        return results
    
    def extract_elements(self, xpath_list: List[str]) -> List:
        """Extrae elementos (no texto) de una lista de xpath"""
        for xpath in xpath_list:
            try:
                elements = self.tree.xpath(xpath)
                if elements:
                    return elements
            except Exception as e:
                logger.debug(f"Error en xpath {xpath}: {e}")
        return []

class BookingExtraerDatosService:
    """Servicio refactorizado para extraer datos de hoteles de Booking.com"""
    
    def __init__(self):
        self.xpath_extractor = XPathExtractor()
    
    def extract_urls_from_json(self, json_data: Union[str, dict]) -> List[str]:
        """Extrae URLs de un JSON de resultados de búsqueda"""
        try:
            if isinstance(json_data, str): 
                data = json.loads(json_data)
            else: 
                data = json_data
            
            urls = []
            if "hotels" in data and isinstance(data["hotels"], list):
                for hotel in data["hotels"]:
                    url = hotel.get("url_arg") or hotel.get("url")
                    if url: 
                        urls.append(url)
            return urls
        except Exception as e:
            logger.error(f"Error extrayendo URLs del JSON: {e}")
            return []
    
    def parse_urls_input(self, input_text: str) -> List[str]:
        """Parsea el input de URLs desde texto o JSON"""
        urls = []
        input_text = input_text.strip()
        
        # Intentar parsear como JSON primero
        if input_text.startswith('{') and input_text.endswith('}'):
            try:
                json_urls = self.extract_urls_from_json(input_text)
                urls.extend(json_urls)
                logger.info(f"Extraídas {len(json_urls)} URLs del JSON")
            except Exception as e: 
                logger.warning(f"Error parseando JSON: {e}")
        
        # Si no hay URLs del JSON, parsear como texto
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
        
        # Eliminar duplicados manteniendo el orden
        seen = set()
        unique_urls = [x for x in urls if not (x in seen or seen.add(x))]
        
        logger.info(f"Total de URLs únicas encontradas: {len(unique_urls)}")
        return unique_urls
    
    def _extract_hotel_name_from_url(self, url: str) -> str:
        """Extrae el nombre del hotel desde la URL"""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and part not in ['hotel', 'es', 'en', 'fr', 'de', 'it']:
                    hotel_name = part.replace('.es.html', '').replace('.html', '').replace('.htm', '').replace('-', ' ')
                    hotel_name = ' '.join(word.capitalize() for word in hotel_name.split())
                    if len(hotel_name) > 3 and not hotel_name.isdigit(): 
                        return hotel_name
            return "Hotel"
        except Exception as e:
            logger.debug(f"Error extrayendo nombre del hotel de URL {url}: {e}")
            return "Hotel"

    def _generate_error_response(self, url: str, error_message: str) -> Dict[str, Any]:
        """Genera una respuesta de error estandarizada"""
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
            "rango_precios": "", "numero_opiniones": "", "valoracion_limpieza": "", 
            "valoracion_confort": "", "valoracion_ubicacion": "", 
            "valoracion_instalaciones_servicios_": "", "valoracion_personal": "", 
            "valoracion_calidad_precio": "", "valoracion_wifi": "", "valoracion_global": "", 
            "images": [], "direccion": "", "codigo_postal": "", "ciudad": "", "pais": "", 
            "enlace_afiliado": url, "sitio_web_oficial": ""
        }
        return {
            "title": f"Error procesando: {hotel_name_from_url}", 
            "slug": self._generate_slug(f"error-procesando-{hotel_name_from_url}"), 
            "status": "draft", 
            "content": f"<p>Ocurrió un error al procesar la información para la URL: {url}.<br>Detalles: {error_message}</p>", 
            "featured_media": 0, "parent": 0, "template": "", "meta": error_meta
        }

    async def scrape_hotels(self, urls: List[str], progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """Función principal de scraping optimizada"""
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, 
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            try:
                for i, url_item in enumerate(urls):
                    try:
                        if progress_callback:
                            hotel_name_prog = self._extract_hotel_name_from_url(url_item)
                            progress_callback({
                                "message": f"📍 Procesando hotel {i+1}/{len(urls)}: {hotel_name_prog}", 
                                "current_url": url_item, "completed": i, "total": len(urls), 
                                "remaining": len(urls) - i - 1
                            })
                        
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
                    progress_callback({
                        "message": f"Completado: {len(urls)} URLs procesadas", 
                        "completed": len(urls), "total": len(urls), "remaining": 0
                    })
            finally: 
                await browser.close()
        return results
    
    async def _extract_javascript_data(self, page) -> Dict[str, Any]:
        """Extrae datos de JavaScript de forma optimizada"""
        js_data_extracted = {}
        try:
            # Extraer datos principales de JavaScript
            js_data_extracted["utag_data"] = await page.evaluate("() => window.utag_data || {}")
            data_layer_raw = await page.evaluate("() => window.dataLayer || []")
            if data_layer_raw: 
                js_data_extracted["dataLayer"] = data_layer_raw[0] if isinstance(data_layer_raw, list) and data_layer_raw else data_layer_raw
            
            # Buscar dirección formateada
            js_data_extracted["formattedAddress"] = await self._search_formatted_address(page)
            
            # Buscar número de reseñas
            js_data_extracted["reviewsCount"] = await self._search_reviews_count(page)
            
            return {k: v for k, v in js_data_extracted.items() if v}
        except Exception as e: 
            logger.error(f"Error extrayendo datos de JavaScript: {e}")
        return {}
    
    async def _search_formatted_address(self, page) -> str:
        """Busca la dirección formateada usando JavaScript optimizado"""
        try:
            # Script JavaScript optimizado para buscar dirección
            js_script = """
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
                    
                    // Buscar en scripts estructurados
                    const scripts = document.querySelectorAll('script[type="application/ld+json"], script[data-capla-application-context]');
                    for (let script of scripts) {
                        try { 
                            const data = JSON.parse(script.textContent); 
                            const result = findFormattedAddress(data); 
                            if (result) return result; 
                        } catch (e) {}
                    }
                    
                    // Buscar en variables globales
                    if (window.__INITIAL_STATE__) { 
                        const result = findFormattedAddress(window.__INITIAL_STATE__); 
                        if (result) return result; 
                    }
                    
                    return '';
                }
            """
            
            formatted_address = await page.evaluate(js_script)
            if formatted_address: 
                return formatted_address
            
            # Fallback a selectores CSS
            address_selectors = [
                '[data-testid="address"]', 
                '.hp_address_subtitle', 
                '.hp-hotel-address', 
                '.address'
            ]
            
            for selector in address_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 10: 
                            return text.strip()
                except: 
                    continue
            return ""
        except Exception as e: 
            logger.error(f"Error buscando formattedAddress: {e}")
            return ""

    async def _search_reviews_count(self, page) -> str:
        """Busca el número de reseñas usando JavaScript optimizado"""
        try:
            js_script = """
                () => {
                    // Buscar en scripts con patrones específicos
                    const allScripts = document.querySelectorAll('script');
                    for (let script of allScripts) {
                        if (script.textContent) {
                            const patterns = [
                                /showReviews:\\s*parseInt\\s*\\(\\s*["'](\\d+)["']\\s*,\\s*[^)]+\\)/,
                                /"reviewCount":\\s*"?(\\d+)"?/,
                                /"reviewsCount":\\s*"?(\\d+)"?/
                            ];
                            for (let pattern of patterns) { 
                                const match = script.textContent.match(pattern); 
                                if (match && match[1]) return match[1]; 
                            }
                        }
                    }
                    return '';
                }
            """
            
            reviews_count = await page.evaluate(js_script)
            return reviews_count if reviews_count else ""
        except Exception as e: 
            logger.error(f"Error buscando reviewsCount: {e}")
            return ""

    def _extract_postal_code_from_address(self, address: str) -> str:
        """Extrae código postal de una dirección"""
        if not address: 
            return ""
        try:
            # Buscar códigos postales de 5 dígitos primero, luego 4
            postal_5_digits = re.findall(r'\b\d{5}\b', address)
            if postal_5_digits: 
                return postal_5_digits[0]
            postal_4_digits = re.findall(r'\b\d{4}\b', address)
            if postal_4_digits: 
                return postal_4_digits[0]
            return ""
        except Exception as e: 
            logger.debug(f"Error extrayendo código postal de '{address}': {e}")
            return ""

    def _generate_slug(self, text: str) -> str:
        """Genera un slug URL-friendly"""
        if not text: 
            return "alojamiento-sin-slug"
        s = text.lower()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'\s+', '-', s)
        s = re.sub(r'-+', '-', s)
        return s.strip('-') or "slug"

    def _parse_hotel_html(self, soup: BeautifulSoup, url: str, js_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Función principal de parsing optimizada con xpath mejorados"""
        # Extraer parámetros de la URL
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Crear árbol lxml para xpath
        tree = html.fromstring(str(soup))
        extractor = DataExtractor(tree)
        
        # Extraer datos estructurados
        data_extraida = self._extract_structured_data(soup)
        
        # Extraer datos usando xpath optimizados
        hotel_data = self._extract_hotel_data_with_xpath(extractor, data_extraida, js_data or {})
        
        # Extraer imagen destacada, imágenes y servicios
        hotel_data["imagen_destacada"] = self._extract_featured_image_optimized(extractor)
        hotel_data["images"] = self._extract_images_optimized(extractor, hotel_data["imagen_destacada"])
        hotel_data["servicios"] = self._extract_facilities_optimized(extractor)
        
        # Extraer valoraciones detalladas
        self._extract_detailed_ratings(extractor, hotel_data)
        
        # Procesar parámetros de búsqueda
        search_params = {
            "busqueda_checkin": query_params.get('checkin', [''])[0],
            "busqueda_checkout": query_params.get('checkout', [''])[0],
            "busqueda_adultos": query_params.get('group_adults', [''])[0],
            "busqueda_ninos": query_params.get('group_children', [''])[0],
            "busqueda_habitaciones": query_params.get('no_rooms', [''])[0]
        }
        
        # Construir respuesta final
        return self._build_final_response(hotel_data, search_params, url, data_extraida)
    
    def _extract_hotel_data_with_xpath(self, extractor: DataExtractor, data_extraida: Dict, js_data: Dict) -> Dict[str, Any]:
        """Extrae datos principales del hotel usando xpath optimizados"""
        js_utag_data = js_data.get("utag_data", {})
        js_data_layer = js_data.get("dataLayer", {})
        
        def get_best_value(js_key_utag, js_key_layer, html_value, fallback=""):
            """Obtiene el mejor valor disponible priorizando JS sobre HTML"""
            val_utag = js_utag_data.get(js_key_utag)
            if val_utag is not None and val_utag != '': 
                return str(val_utag)
            val_layer = js_data_layer.get(js_key_layer)
            if val_layer is not None and val_layer != '': 
                return str(val_layer)
            if html_value is not None and html_value != '': 
                return str(html_value)
            return fallback
        
        # Extraer datos principales
        hotel_data = {
            "nombre_alojamiento": get_best_value("hotel_name", "hotel_name", 
                                                extractor.extract_first_match(self.xpath_extractor.HOTEL_NAME)),
            "precio_noche": self._extract_price_optimized(extractor),
            "valoracion_global": extractor.extract_first_match(self.xpath_extractor.GLOBAL_RATING).replace(",", "."),
            "numero_opiniones": self._extract_reviews_count_optimized(extractor),
            "direccion": get_best_value("formattedAddress", "formattedAddress", 
                                       extractor.extract_first_match(self.xpath_extractor.ADDRESS)),
            "ciudad": get_best_value("city_name", "city_name", ""),
            "pais": get_best_value("country_name", "country_name", ""),
            "alojamiento_destacado": "Preferente" if extractor.extract_elements(self.xpath_extractor.PREFERRED_STATUS) else "No",
            "isla_relacionada": self._extract_island_from_keywords(extractor),
            "frases_destacadas": extractor.extract_all_matches(self.xpath_extractor.HIGHLIGHTS),
            "tipo_alojamiento": get_best_value("hotel_type", "hotel_type", 
                                              data_extraida.get("@type", "hotel"), "hotel").lower(),
            "estrellas": get_best_value("hotel_class", "hotel_class", 
                                       data_extraida.get("starRating", {}).get("ratingValue", ""))
        }
        
        # Procesar código postal
        hotel_data["codigo_postal"] = self._extract_postal_code_from_address(hotel_data["direccion"])
        
        return hotel_data
    
    def _extract_price_optimized(self, extractor: DataExtractor) -> str:
        """Extrae el precio usando xpath optimizados"""
        price_text = extractor.extract_first_match(self.xpath_extractor.PRICE)
        if price_text:
            # Limpiar el precio manteniendo solo números, comas y puntos
            cleaned_price = re.sub(r'[^\d,.]', '', price_text).replace(',', '.')
            if cleaned_price:
                logger.info(f"Precio extraído: {cleaned_price} (raw: {price_text})")
                return cleaned_price
        logger.warning("No se encontró precio en la página")
        return ""
    
    def _extract_reviews_count_optimized(self, extractor: DataExtractor) -> str:
        """Extrae el número de opiniones usando xpath optimizados"""
        reviews_text = extractor.extract_first_match(self.xpath_extractor.REVIEWS_COUNT)
        if reviews_text:
            # Extraer solo números del texto
            match = re.search(r'([\d\.,]+)', reviews_text)
            if match: 
                return match.group(1).replace('.', '').replace(',', '')
        return ""
    
    def _extract_island_from_keywords(self, extractor: DataExtractor) -> str:
        """Extrae información de isla desde meta keywords"""
        try:
            keywords_elements = extractor.tree.xpath('//meta[@name="keywords"]/@content')
            if keywords_elements:
                keywords_content = keywords_elements[0]
                match = re.search(r'I:([^,]+)', keywords_content)
                if match: 
                    return match.group(1).strip()
        except Exception as e:
            logger.debug(f"Error extrayendo isla_relacionada: {e}")
        return ""
    
    def _extract_featured_image_optimized(self, extractor: DataExtractor) -> Dict[str, str]:
        """Extrae la imagen destacada (principal) del hotel usando xpath optimizados"""
        try:
            # Buscar elementos de imagen completos para extraer atributos
            img_elements = extractor.extract_elements([
                "//div[contains(@class, 'hotel-header-image')]//img",
                "//div[@data-testid='property-gallery']//img[1]",
                "//div[contains(@class, 'gallery-container')]//img[1]",
                "//img[contains(@src, 'bstatic.com/xdata/images/hotel')][1]",
                "//img[contains(@data-src, 'bstatic.com/xdata/images/hotel')][1]"
            ])
            
            if img_elements:
                img_element = img_elements[0]
                image_data = self._extract_image_attributes(img_element)
                if image_data["image_url"]:
                    logger.info(f"Imagen destacada extraída: {image_data['image_url']}")
                    return image_data
            
            # Fallback: usar xpath directo para URL si no se encuentra elemento completo
            featured_image_url = extractor.extract_first_match(self.xpath_extractor.FEATURED_IMAGE)
            if featured_image_url and "bstatic.com/xdata/images/hotel" in featured_image_url and ".jpg" in featured_image_url:
                normalized_url = self._normalize_image_url(featured_image_url)
                filename = self._extract_filename_from_url(normalized_url)
                logger.info(f"Imagen destacada (fallback URL) extraída: {normalized_url}")
                return {
                    "image_url": normalized_url,
                    "title": "",
                    "alt_text": "",
                    "caption": "",
                    "description": "",
                    "filename": filename
                }
            
            logger.warning("No se encontró imagen destacada")
            return {
                "image_url": "",
                "title": "",
                "alt_text": "",
                "caption": "",
                "description": "",
                "filename": ""
            }
            
        except Exception as e:
            logger.error(f"Error extrayendo imagen destacada: {e}")
            return {
                "image_url": "",
                "title": "",
                "alt_text": "",
                "caption": "",
                "description": "",
                "filename": ""
            }
    
    def _extract_images_optimized(self, extractor: DataExtractor, featured_image: Dict[str, str], max_images: int = 15) -> List[Dict[str, str]]:
        """Extrae imágenes usando xpath optimizados y elimina duplicados con imagen destacada"""
        imagenes = []
        found_urls = set()
        
        # Añadir la URL de la imagen destacada al set para evitar duplicados
        featured_image_url = featured_image.get("image_url", "") if featured_image else ""
        if featured_image_url:
            found_urls.add(featured_image_url)
            logger.info(f"Imagen destacada añadida a exclusiones: {featured_image_url}")
        
        try:
            # Extraer elementos de imagen usando xpath
            img_elements = extractor.extract_elements(self.xpath_extractor.IMAGES)
            
            for img_element in img_elements:
                if len(imagenes) >= max_images:
                    break
                    
                # Extraer todos los atributos de la imagen
                image_data = self._extract_image_attributes(img_element)
                
                if image_data["image_url"] and image_data["image_url"] not in found_urls:
                    imagenes.append(image_data)
                    found_urls.add(image_data["image_url"])
                    logger.debug(f"Imagen añadida a galería: {image_data['image_url']}")
                else:
                    logger.debug(f"Imagen duplicada omitida: {image_data.get('image_url', 'URL vacía')}")
            
        except Exception as e:
            logger.error(f"Error extrayendo imágenes: {e}")
        
        logger.info(f"Total imágenes extraídas para galería: {len(imagenes)} (excluyendo imagen destacada)")
        return imagenes[:max_images]
    
    def _extract_image_attributes(self, img_element) -> Dict[str, str]:
        """Extrae todos los atributos de un elemento imagen"""
        try:
            # Obtener src de diferentes atributos
            src = None
            title = ""
            alt_text = ""
            
            if hasattr(img_element, 'get'):
                # Elemento lxml
                src = img_element.get("src") or img_element.get("data-src") or img_element.get("data-lazy")
                title = img_element.get("title", "")
                alt_text = img_element.get("alt", "")
            elif hasattr(img_element, 'attrib'):
                # Elemento con atributos
                src = img_element.attrib.get("src") or img_element.attrib.get("data-src")
                title = img_element.attrib.get("title", "")
                alt_text = img_element.attrib.get("alt", "")
            
            if src and "bstatic.com/xdata/images/hotel" in src and ".jpg" in src:
                # Normalizar URL de imagen
                normalized_src = self._normalize_image_url(src)
                filename = self._extract_filename_from_url(normalized_src)
                
                # Limpiar y procesar atributos
                title = title.strip() if title else ""
                alt_text = alt_text.strip() if alt_text else ""
                
                # Generar caption y description basados en title/alt si están disponibles
                caption = title if title else alt_text if alt_text else ""
                description = alt_text if alt_text else title if title else ""
                
                return {
                    "image_url": normalized_src,
                    "title": title,
                    "alt_text": alt_text,
                    "caption": caption,
                    "description": description,
                    "filename": filename
                }
            
            return {
                "image_url": "",
                "title": "",
                "alt_text": "",
                "caption": "",
                "description": "",
                "filename": ""
            }
            
        except Exception as e:
            logger.debug(f"Error extrayendo atributos de imagen: {e}")
            return {
                "image_url": "",
                "title": "",
                "alt_text": "",
                "caption": "",
                "description": "",
                "filename": ""
            }
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extrae el nombre del archivo desde la URL"""
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
            # Extraer el nombre del archivo de la ruta
            filename = path.split('/')[-1] if '/' in path else path
            # Limpiar parámetros si los hay
            if '?' in filename:
                filename = filename.split('?')[0]
            return filename
        except Exception as e:
            logger.debug(f"Error extrayendo filename de URL {url}: {e}")
            return ""
    
    def _normalize_image_url(self, src: str) -> str:
        """Normaliza URLs de imágenes para obtener la mejor calidad"""
        try:
            parsed_url = urlparse(src)
            base_path = parsed_url.path
            
            # Asegurar resolución max1024x768
            if "/max1024x768/" not in base_path:
                base_path = re.sub(r"/max[^/]+/", "/max1024x768/", base_path)
            
            # Mantener solo parámetro k si existe
            query_params = parse_qs(parsed_url.query)
            final_query_string = ""
            if 'k' in query_params:
                k_value = query_params['k'][0]
                final_query_string = urlencode({'k': k_value})
            
            return urlunparse((parsed_url.scheme, parsed_url.netloc, base_path, '', final_query_string, ''))
        except Exception as e:
            logger.debug(f"Error normalizando URL de imagen {src}: {e}")
            return src
    
    def _extract_facilities_optimized(self, extractor: DataExtractor) -> List[str]:
        """Extrae servicios/instalaciones usando xpath optimizados"""
        servicios_set = set()
        
        try:
            # Extraer servicios usando xpath
            facilities_texts = extractor.extract_all_matches(self.xpath_extractor.FACILITIES)
            
            for texto in facilities_texts:
                if texto and 2 < len(texto) < 50: 
                    servicios_set.add(texto)
            
            # Fallback si no se encontraron servicios
            if not servicios_set:
                possible_classes = ["bui-list__description", "db29ecfbe2", "facility_name"]
                for class_name in possible_classes:
                    elements = extractor.tree.xpath(f"//span[contains(@class, '{class_name}')]/text() | //div[contains(@class, '{class_name}')]/text()")
                    for element in elements:
                        texto = str(element).strip()
                        if texto and 2 < len(texto) < 50: 
                            servicios_set.add(texto)
                            
        except Exception as e: 
            logger.error(f"Error extrayendo servicios: {e}")
        
        return sorted(list(servicios_set))
    
    def _extract_detailed_ratings(self, extractor: DataExtractor, hotel_data: Dict[str, Any]) -> None:
        """Extrae valoraciones detalladas usando xpath optimizados"""
        try:
            for rating_key, xpath_list in self.xpath_extractor.DETAILED_RATINGS.items():
                rating_value = extractor.extract_first_match(xpath_list)
                if rating_value:
                    # Limpiar y normalizar el valor
                    cleaned_value = rating_value.strip().replace(",", ".")
                    
                    # Mapear a los campos correctos del JSON
                    field_mapping = {
                        'personal': 'valoracion_personal',
                        'limpieza': 'valoracion_limpieza', 
                        'confort': 'valoracion_confort',
                        'ubicacion': 'valoracion_ubicacion',
                        'instalaciones_servicios': 'valoracion_instalaciones_servicios_',
                        'calidad_precio': 'valoracion_calidad_precio',
                        'wifi': 'valoracion_wifi'
                    }
                    
                    field_name = field_mapping.get(rating_key)
                    if field_name:
                        hotel_data[field_name] = cleaned_value
                        logger.info(f"Valoración '{rating_key}' extraída: {cleaned_value}")
                        
        except Exception as e:
            logger.error(f"Error extrayendo valoraciones detalladas: {e}")
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae datos estructurados JSON-LD"""
        try:
            scripts_ldjson = soup.find_all('script', type='application/ld+json')
            for script in scripts_ldjson:
                if script.string:
                    try:
                        data_json = json.loads(script.string)
                        type_val = data_json.get("@type")
                        if isinstance(type_val, list):
                            if "Hotel" in type_val or "LodgingBusiness" in type_val: 
                                return data_json
                        elif type_val in ["Hotel", "LodgingBusiness"]: 
                            return data_json
                    except json.JSONDecodeError: 
                        logger.debug(f"Error decodificando JSON-LD: {script.string[:100]}...")
        except Exception as e: 
            logger.error(f"Error extrayendo datos estructurados: {e}")
        return {}
    
    def _build_final_response(self, hotel_data: Dict[str, Any], search_params: Dict[str, str], 
                             url: str, data_extraida: Dict[str, Any]) -> Dict[str, Any]:
        """Construye la respuesta final manteniendo el formato JSON original"""
        
        # Extraer subtítulos H2
        h2s_list = []
        try:
            h2_elements = BeautifulSoup(str(hotel_data.get('html_content', '')), 'html.parser').find_all("h2")
            h2s_list = [h2.get_text(strip=True) for h2 in h2_elements if h2.get_text(strip=True)]
        except:
            pass
        
        # Construir título y slug
        nombre_alojamiento = hotel_data.get("nombre_alojamiento", "")
        ciudad = hotel_data.get("ciudad", "")
        title_str = f"{nombre_alojamiento} – Lujo exclusivo en {ciudad}" if nombre_alojamiento and ciudad else nombre_alojamiento or "Alojamiento sin título"
        slug_str = self._generate_slug(title_str)
        
        # Construir descripción
        descripcion_corta_raw = data_extraida.get("description", "")
        if not descripcion_corta_raw:
            # Buscar en meta description como fallback
            try:
                soup_temp = BeautifulSoup(str(hotel_data.get('html_content', '')), 'html.parser')
                desc_tag = soup_temp.find("meta", {"name": "description"})
                if desc_tag and desc_tag.get("content"):
                    descripcion_corta_raw = desc_tag.get("content")
            except:
                pass
        
        descripcion_corta_html = f"<p>{descripcion_corta_raw}</p>" if descripcion_corta_raw else "<p></p>"
        content_html = f"<p>{nombre_alojamiento} es un alojamiento destacado en {ciudad}. {descripcion_corta_raw}</p>" if nombre_alojamiento and ciudad else descripcion_corta_html
        
        # Construir metadata completa
        meta_data = {
            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            **search_params,
            "nombre_alojamiento": nombre_alojamiento,
            "tipo_alojamiento": hotel_data.get("tipo_alojamiento", "hotel"),
            "titulo_h1": nombre_alojamiento,
            "subtitulos_h2": h2s_list,
            "slogan_principal": "",
            "descripcion_corta": descripcion_corta_html,
            "estrellas": hotel_data.get("estrellas", ""),
            "precio_noche": hotel_data.get("precio_noche", ""),
            "alojamiento_destacado": hotel_data.get("alojamiento_destacado", "No"),
            "isla_relacionada": hotel_data.get("isla_relacionada", ""),
            "frases_destacadas": hotel_data.get("frases_destacadas", []),
            "servicios": hotel_data.get("servicios", []),
            "rango_precios": f"{hotel_data.get('precio_noche', '')} EUR" if hotel_data.get("precio_noche") else "",
            "numero_opiniones": hotel_data.get("numero_opiniones", ""),
            "valoracion_limpieza": hotel_data.get("valoracion_limpieza", ""),
            "valoracion_confort": hotel_data.get("valoracion_confort", ""),
            "valoracion_ubicacion": hotel_data.get("valoracion_ubicacion", ""),
            "valoracion_instalaciones_servicios_": hotel_data.get("valoracion_instalaciones_servicios_", ""),
            "valoracion_personal": hotel_data.get("valoracion_personal", ""),
            "valoracion_calidad_precio": hotel_data.get("valoracion_calidad_precio", ""),
            "valoracion_wifi": hotel_data.get("valoracion_wifi", ""),
            "valoracion_global": hotel_data.get("valoracion_global", ""),
            "imagen_destacada": hotel_data.get("imagen_destacada", ""),
            "images": hotel_data.get("images", []),
            "direccion": hotel_data.get("direccion", ""),
            "codigo_postal": hotel_data.get("codigo_postal", ""),
            "ciudad": ciudad,
            "pais": hotel_data.get("pais", ""),
            "enlace_afiliado": url,
            "sitio_web_oficial": ""
        }
        
        # Respuesta final en el formato esperado
        return {
            "title": title_str,
            "slug": slug_str,
            "status": "publish",
            "content": content_html,
            "featured_media": 0,
            "parent": 0,
            "template": "",
            "meta": meta_data
        }

    def notify_n8n_webhook(self, ids: List[Any]) -> Dict[str, Any]:
        """Notifica a n8n webhook con los IDs procesados"""
        if not ids: 
            logger.warning("No IDs provided to send to n8n.")
            return {"success": False, "message": "No IDs proporcionados para enviar a n8n."}
        
        try:
            n8n_url = settings.N8N_WEBHOOK_URL
            if not n8n_url: 
                logger.warning("La URL del webhook de n8n no está configurada.")
                return {"success": False, "message": "La URL del webhook de n8n no está configurada."}
            
            data_to_send = [{"_id": str(mongo_id)} for mongo_id in ids]
            response = httpx_requests.post(n8n_url, json=data_to_send, timeout=10)
            response.raise_for_status()
            
            success_message = f"✅ {len(ids)} IDs enviados a n8n."
            logger.info(f"{success_message} Datos: {data_to_send}")
            return {"success": True, "message": success_message}
            
        except Exception as e: 
            error_message = f"❌ Error al enviar IDs a n8n: {e}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
