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
from services.serialice_get_engine import SerializeGetEngine

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
        "//span[@data-testid='price-text']/text()",
        "//span[contains(@class, 'fcab3ed991') and contains(@class, 'bd73d13072')]/text()",
        "//div[contains(@class, 'bui-price-display__value')]/text()",
        "//span[contains(@class, 'bui-price-display__value')]/text()",
        "//div[@data-testid='price-and-discounted-price']//span/text()",
        "//span[contains(text(), '€') or contains(text(), 'EUR')]/text()",
        "//div[contains(@class, 'price')]//span[contains(text(), '€')]/text()",
        "//span[contains(@aria-label, 'precio') or contains(@aria-label, 'price')]/text()"
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
    
    # Xpath para dirección (mejorados para capturar la dirección visible debajo del título)
    ADDRESS = [
        "//span[@data-testid='address']/text()",
        "//div[contains(@class, 'hp_address_subtitle')]/text()",
        "//p[contains(@class, 'hp_address_subtitle')]/text()",
        "//span[contains(@class, 'hp_address_subtitle')]/text()",
        "//div[@data-testid='property-location']//span/text()",
        "//div[contains(@class, 'hp-hotel-address')]/text()",
        "//div[contains(@class, 'hp-address')]//span/text()",
        "//span[contains(@class, 'address-text')]/text()",
        "//div[contains(@class, 'location')]//span/text()",
        "//address//text()",
        "//div[contains(@class, 'property-address')]//text()",
        "//div[contains(@class, 'address')]/text()",
        "//h1/following-sibling::*//span[contains(text(), 'Carretera') or contains(text(), 'Calle') or contains(text(), 'Avenida') or contains(text(), 'Plaza') or contains(text(), 'Street') or contains(text(), 'Avenue') or contains(text(), 'Road') or contains(text(), 'Boulevard')]/text()",
        "//h1/following-sibling::div//span[contains(@class, 'f419a93f12')]/text()",
        "//div[contains(@class, 'a53cbfa6de')]//span/text()",
        "//span[contains(text(), ',') and (string-length(text()) > 20)]/text()",
        "//h1/following-sibling::*[position() <= 3]//span[contains(text(), ',')]/text()",
        "//div[contains(@class, 'hp-hotel-location')]//span/text()",
        "//span[contains(@class, 'location-text') or contains(@class, 'address-line')]/text()"
    ]
    
    # Xpath para alojamiento destacado/preferente
    PREFERRED_STATUS = [
        "//span[@data-testid='preferred-icon']",
        "//div[contains(@class, 'preferred-badge')]",
        "//span[contains(@class, 'preferred')]"
    ]
    
    # Xpath para frases destacadas (excluyendo botones de acción)
    HIGHLIGHTS = [
        "//div[@data-testid='PropertyHighlightList-wrapper']//ul/li//div[contains(@class, 'b99b6ef58f')]//span[contains(@class, 'f6b6d2a959') and not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar'))]/text()",
        "//div[contains(@class, 'hp--desc_highlights')]//div[contains(@class,'ph-item-copy-container')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar'))]/text()",
        "//div[contains(@class, 'property-highlights')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar')) and not(ancestor::button) and not(ancestor::a)]/text()",
        "//div[contains(@class, 'hp_desc_important_facilities')]//span[not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar'))]/text()",
        "//ul[contains(@class, 'bui-list')]//span[contains(@class, 'bui-list__description') and not(contains(text(), 'Reserva')) and not(contains(text(), 'Guardar'))]/text()"
    ]
    
    # Xpath para H2 y contenido asociado
    H2_ELEMENTS = [
        "//h2",
        "//div[contains(@class, 'hp-description')]//h2",
        "//div[contains(@class, 'hotel-description')]//h2",
        "//section//h2"
    ]
    
    # Xpath para H3 elementos
    H3_ELEMENTS = [
        "//h3",
        "//div[contains(@class, 'hp-description')]//h3",
        "//div[contains(@class, 'hotel-description')]//h3",
        "//section//h3"
    ]
    
    # Xpath para servicios/instalaciones
    FACILITIES = [
        "//div[contains(@class, 'hotel-facilities__list')] li .bui-list__description/text()",
        "//div[contains(@class, 'facilitiesChecklistSection')] li span/text()",
        "//div[contains(@class, 'hp_desc_important_facilities')] li/text()",
        "//div[@data-testid='property-most-popular-facilities-wrapper'] div[@data-testid='facility-badge'] span/text()",
        "//div[@data-testid='facilities-block'] li div[2] span/text()",
        "//div[@data-testid='property-most-popular-facilities-wrapper']//span[contains(@class, 'db29ecfbe2')]/text()",
        "//div[contains(@class, 'hp_desc_important_facilities')]//span/text()",
        "//ul[contains(@class, 'hotel-facilities-group')]//span/text()",
        "//div[contains(@class, 'facilitiesChecklistSection')]//div[contains(@class, 'bui-list__description')]/text()",
        "//div[@data-testid='facilities-block']//span[contains(@class, 'db29ecfbe2')]/text()",
        "//div[contains(@class, 'hp-description')]//li/text()",
        "//div[contains(@class, 'important_facilities')]//span/text()",
        "//span[contains(@class, 'hp-desc-highlighted-text')]/text()"
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
        """Genera una respuesta de error estandarizada con el nuevo formato"""
        hotel_name_from_url = self._extract_hotel_name_from_url(url)
        error_meta = {
            "nombre_alojamiento": f"Error al procesar: {hotel_name_from_url}",
            "tipo_alojamiento": "hotel",
            "slogan_principal": "",
            "descripcion_corta": f"<p>Error procesando URL: {error_message}</p>\n",
            "estrellas": "",
            "precio_noche": "",
            "alojamiento_destacado": "No",
            "isla_relacionada": "",
            "frases_destacadas": {},
            "servicios": [],
            "valoracion_limpieza": "",
            "valoracion_confort": "",
            "valoracion_ubicacion": "",
            "valoracion_instalaciones_servicios_": "",
            "valoracion_personal": "",
            "valoracion_calidad_precio": "",
            "valoracion_wifi": "",
            "valoracion_global": "",
            "images": {},
            "direccion": "",
            "enlace_afiliado": url,
            "sitio_web_oficial": "",
            "titulo_h1": f"Error al procesar: {hotel_name_from_url}",
            "bloques_contenido_h2": {}
        }
        return {
            "title": f"Error procesando: {hotel_name_from_url}",
            "content": f"\n<p>Ocurrió un error al procesar la información para la URL: {url}.<br>Detalles: {error_message}</p>\n",
            "status": "draft",
            "type": "alojamientos",
            "slug": self._generate_slug(f"error-procesando-{hotel_name_from_url}"),
            "obj_featured_media": {},
            "meta": error_meta
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
    
    def _build_h2_flat_structure(self, h2_sections: List[Dict[str, str]]) -> Dict[str, str]:
        """Construye estructura JSON para bloques H2 usando el servicio de serialización"""
        return SerializeGetEngine.create_h2_blocks_json(h2_sections)

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
        hotel_data["imagen_destacada"] = self._extract_featured_image_optimized(extractor, hotel_data.get("nombre_alojamiento", ""))
        hotel_data["images"] = self._extract_images_optimized(extractor, hotel_data["imagen_destacada"], hotel_data.get("nombre_alojamiento", ""))
        hotel_data["servicios"] = self._extract_facilities_optimized(extractor)
        
        # Extraer H2 con contenido asociado
        hotel_data["h2_sections"] = self._extract_h2_with_content(soup)
        
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
        """Extrae el precio usando xpath optimizados y métodos adicionales"""
        # Intentar con xpath primero
        price_text = extractor.extract_first_match(self.xpath_extractor.PRICE)
        if price_text:
            # Limpiar el precio manteniendo solo números, comas y puntos
            cleaned_price = re.sub(r'[^\d,.]', '', price_text).replace(',', '.')
            if cleaned_price:
                logger.info(f"Precio extraído: {cleaned_price} (raw: {price_text})")
                return cleaned_price
        
        # Fallback: buscar en todo el HTML con patrones de precio
        try:
            html_content = html.tostring(extractor.tree, encoding='unicode')
            
            # Patrones de precio más amplios
            price_patterns = [
                r'€\s*(\d+(?:[.,]\d+)?)',  # €123 o €123.45
                r'(\d+(?:[.,]\d+)?)\s*€',  # 123€ o 123.45€
                r'EUR\s*(\d+(?:[.,]\d+)?)',  # EUR 123
                r'(\d+(?:[.,]\d+)?)\s*EUR',  # 123 EUR
                r'"price"[^:]*:\s*"?(\d+(?:[.,]\d+)?)"?',  # JSON price
                r'"amount"[^:]*:\s*"?(\d+(?:[.,]\d+)?)"?',  # JSON amount
                r'data-price[^=]*=\s*["\'](\d+(?:[.,]\d+)?)["\']',  # data-price attribute
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    # Tomar el primer precio válido encontrado
                    for match in matches:
                        cleaned_price = match.replace(',', '.')
                        try:
                            # Verificar que es un número válido
                            float(cleaned_price)
                            if float(cleaned_price) > 0:
                                logger.info(f"Precio extraído (fallback): {cleaned_price}")
                                return cleaned_price
                        except ValueError:
                            continue
                            
        except Exception as e:
            logger.debug(f"Error en fallback de precio: {e}")
        
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
    
    def _extract_featured_image_optimized(self, extractor: DataExtractor, nombre_alojamiento: str) -> Dict[str, str]:
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
                image_data = self._extract_image_attributes(img_element, nombre_alojamiento, 1)
                if image_data["image_url"]:
                    logger.info(f"Imagen destacada extraída: {image_data['image_url']}")
                    return image_data
            
            # Fallback: usar xpath directo para URL si no se encuentra elemento completo
            featured_image_url = extractor.extract_first_match(self.xpath_extractor.FEATURED_IMAGE)
            if featured_image_url and "bstatic.com/xdata/images/hotel" in featured_image_url and ".jpg" in featured_image_url:
                normalized_url = self._normalize_image_url(featured_image_url)
                clean_hotel_name = self._clean_hotel_name_for_filename(nombre_alojamiento)
                filename = f"{clean_hotel_name}_001.jpg"
                title = f"{clean_hotel_name}_001"
                logger.info(f"Imagen destacada (fallback URL) extraída: {normalized_url}")
                return {
                    "image_url": normalized_url,
                    "title": title,
                    "alt_text": "",
                    "caption": title,
                    "description": title,
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
    
    def _extract_images_optimized(self, extractor: DataExtractor, featured_image: Dict[str, str], nombre_alojamiento: str, max_images: int = 15) -> List[Dict[str, str]]:
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
            
            # Contador secuencial que empieza en 2 (porque la imagen destacada es 001)
            image_counter = 2
            
            for img_element in img_elements:
                if len(imagenes) >= max_images:
                    break
                    
                # Extraer todos los atributos de la imagen
                image_data = self._extract_image_attributes(img_element, nombre_alojamiento, image_counter)
                
                if image_data["image_url"] and image_data["image_url"] not in found_urls:
                    imagenes.append(image_data)
                    found_urls.add(image_data["image_url"])
                    logger.debug(f"Imagen añadida a galería: {image_data['image_url']} con contador {image_counter}")
                    image_counter += 1  # Solo incrementar cuando se añade una imagen válida
                else:
                    logger.debug(f"Imagen duplicada omitida: {image_data.get('image_url', 'URL vacía')}")
            
        except Exception as e:
            logger.error(f"Error extrayendo imágenes: {e}")
        
        logger.info(f"Total imágenes extraídas para galería: {len(imagenes)} (excluyendo imagen destacada)")
        return imagenes[:max_images]
    
    def _extract_image_attributes(self, img_element, nombre_alojamiento: str = "", image_counter: int = 1) -> Dict[str, str]:
        """Extrae todos los atributos de un elemento imagen"""
        try:
            # Obtener src de diferentes atributos
            src = None
            alt_text = ""
            
            if hasattr(img_element, 'get'):
                # Elemento lxml
                src = img_element.get("src") or img_element.get("data-src") or img_element.get("data-lazy")
                alt_text = img_element.get("alt", "")
            elif hasattr(img_element, 'attrib'):
                # Elemento con atributos
                src = img_element.attrib.get("src") or img_element.attrib.get("data-src")
                alt_text = img_element.attrib.get("alt", "")
            
            if src and "bstatic.com/xdata/images/hotel" in src and ".jpg" in src:
                # Normalizar URL de imagen
                normalized_src = self._normalize_image_url(src)
                
                # Generar filename y title con formato personalizado
                clean_hotel_name = self._clean_hotel_name_for_filename(nombre_alojamiento)
                filename = f"{clean_hotel_name}_{image_counter:03d}.jpg"
                title = f"{clean_hotel_name}_{image_counter:03d}"
                
                # Limpiar alt_text
                alt_text = alt_text.strip() if alt_text else ""
                
                # Generar caption y description
                caption = title
                description = alt_text if alt_text else title
                
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
    
    def _clean_hotel_name_for_filename(self, nombre_alojamiento: str) -> str:
        """Limpia el nombre del hotel para usar como filename"""
        if not nombre_alojamiento:
            return "hotel"
        
        # Convertir a minúsculas y reemplazar espacios y caracteres especiales
        clean_name = nombre_alojamiento.lower()
        clean_name = re.sub(r'[^\w\s-]', '', clean_name)  # Eliminar caracteres especiales
        clean_name = re.sub(r'\s+', '_', clean_name)      # Espacios a guiones bajos
        clean_name = re.sub(r'_+', '_', clean_name)       # Múltiples guiones bajos a uno
        clean_name = clean_name.strip('_')                # Eliminar guiones bajos al inicio/final
        
        # Limitar longitud
        if len(clean_name) > 50:
            clean_name = clean_name[:50].rstrip('_')
        
        return clean_name if clean_name else "hotel"
    
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
    
    def _extract_h2_with_content(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrae H2 con su contenido asociado, manteniendo H3 con etiquetas HTML"""
        h2_sections = []
        
        try:
            # Buscar todos los H2 en la página
            h2_elements = soup.find_all('h2')
            
            for h2 in h2_elements:
                h2_text = h2.get_text(strip=True)
                if not h2_text or len(h2_text) < 3:
                    continue
                
                # Obtener el contenido asociado al H2
                content_parts = []
                current_element = h2.next_sibling
                
                # Recorrer elementos hermanos hasta encontrar otro H2 o final
                while current_element:
                    if hasattr(current_element, 'name'):
                        # Si encontramos otro H2, parar
                        if current_element.name == 'h2':
                            break
                        
                        # Si es un H3, mantener las etiquetas HTML
                        elif current_element.name == 'h3':
                            h3_text = current_element.get_text(strip=True)
                            if h3_text:
                                content_parts.append(f"<h3>{h3_text}</h3>")
                        
                        # Para otros elementos, extraer texto
                        elif current_element.name in ['p', 'div', 'span', 'ul', 'ol', 'li']:
                            element_text = current_element.get_text(strip=True)
                            if element_text and len(element_text) > 10:
                                # Si contiene H3 internos, procesarlos
                                h3_internal = current_element.find_all('h3')
                                if h3_internal:
                                    # Procesar el HTML manteniendo H3
                                    element_html = str(current_element)
                                    # Limpiar HTML pero mantener H3
                                    cleaned_html = re.sub(r'<(?!h3|/h3)[^>]*>', '', element_html)
                                    cleaned_html = re.sub(r'\s+', ' ', cleaned_html).strip()
                                    if cleaned_html:
                                        content_parts.append(cleaned_html)
                                else:
                                    content_parts.append(element_text)
                    
                    current_element = current_element.next_sibling
                
                # Si encontramos contenido, añadir la sección
                if content_parts:
                    content_text = ' '.join(content_parts).strip()
                    if content_text and len(content_text) > 20:
                        h2_sections.append({
                            "titulo": h2_text,
                            "contenido": content_text
                        })
                        logger.debug(f"H2 extraído: '{h2_text}' con {len(content_text)} caracteres de contenido")
            
        except Exception as e:
            logger.error(f"Error extrayendo H2 con contenido: {e}")
        
        logger.info(f"Total H2 con contenido extraídos: {len(h2_sections)}")
        return h2_sections
    
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
        """Construye la respuesta final con el nuevo formato JSON"""
        
        # Extraer subtítulos H2 con contenido asociado
        h2_sections = hotel_data.get("h2_sections", [])
        h2s_list = [section["titulo"] for section in h2_sections] if h2_sections else []
        
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
        
        descripcion_corta_html = f"<p>{descripcion_corta_raw}</p>\n" if descripcion_corta_raw else "<p></p>\n"
        content_html = f"\n<p><strong>{nombre_alojamiento}</strong></p>\n\n\n\n<p>{descripcion_corta_raw}</p>\n" if nombre_alojamiento else descripcion_corta_html
        
        # Construir estructura H2 serializada
        h2_structure = self._build_h2_flat_structure(h2_sections)
        logger.info(f"Estructura H2 construida: {h2_structure}")
        
        # Convertir frases destacadas de array a objeto con item-X
        frases_obj = {}
        for i, frase in enumerate(hotel_data.get("frases_destacadas", [])):
            frases_obj[f"item-{i}"] = {"frase_destacada": frase}
        
        # Convertir images de array a objeto con item-X
        images_obj = {}
        for i, img in enumerate(hotel_data.get("images", [])):
            images_obj[f"item-{i}"] = img
        
        # Obtener imagen destacada
        imagen_destacada = hotel_data.get("imagen_destacada", {})
        
        # Construir metadata completa
        meta_data = {
            "nombre_alojamiento": nombre_alojamiento,
            "tipo_alojamiento": hotel_data.get("tipo_alojamiento", "hotel"),
            "slogan_principal": "",
            "descripcion_corta": descripcion_corta_html,
            "estrellas": hotel_data.get("estrellas", ""),
            "precio_noche": hotel_data.get("precio_noche", ""),
            "alojamiento_destacado": hotel_data.get("alojamiento_destacado", "No"),
            "isla_relacionada": hotel_data.get("isla_relacionada", ""),
            "frases_destacadas": frases_obj,
            "servicios": hotel_data.get("servicios", []),
            "valoracion_limpieza": hotel_data.get("valoracion_limpieza", ""),
            "valoracion_confort": hotel_data.get("valoracion_confort", ""),
            "valoracion_ubicacion": hotel_data.get("valoracion_ubicacion", ""),
            "valoracion_instalaciones_servicios_": hotel_data.get("valoracion_instalaciones_servicios_", ""),
            "valoracion_personal": hotel_data.get("valoracion_personal", ""),
            "valoracion_calidad_precio": hotel_data.get("valoracion_calidad_precio", ""),
            "valoracion_wifi": hotel_data.get("valoracion_wifi", ""),
            "valoracion_global": hotel_data.get("valoracion_global", ""),
            "images": images_obj,
            "direccion": hotel_data.get("direccion", ""),
            "enlace_afiliado": url,
            "sitio_web_oficial": "",
            "titulo_h1": nombre_alojamiento,
            **h2_structure
        }
        
        # Respuesta final en el formato esperado
        return {
            "title": title_str,
            "content": content_html,
            "status": "publish",
            "type": "alojamientos",
            "slug": slug_str,
            "obj_featured_media": imagen_destacada if imagen_destacada else {},
            "meta": meta_data
        }

    def notify_n8n_webhook(self, ids: List[Any]) -> Dict[str, Any]:
        """Notifica a n8n webhook con los IDs procesados"""
        if not ids: 
            logger.warning("No IDs provided to send to n8n.")
            return {"success": False, "message": "No IDs proporcionados para enviar a n8n."}
        
        try:
            n8n_url = settings.N8N_WEBHOOK_URL_IMAGEN_BOOKING
            if not n8n_url: 
                logger.warning("La URL del webhook de n8n no está configurada.")
                return {"success": False, "message": "La URL del webhook de n8n no está configurada."}
            
            data_to_send = [{"_id": str(mongo_id)} for mongo_id in ids]
            response = httpx_requests.post(n8n_url, json=data_to_send, timeout=10)
            response.raise_for_status()
            
            # Capturar el JSON de respuesta
            try:
                response_json = response.json()
                logger.info(f"Respuesta JSON del webhook: {response_json}")
            except Exception as json_error:
                logger.warning(f"No se pudo parsear la respuesta como JSON: {json_error}")
                response_json = {"raw_response": response.text}
            
            success_message = f"✅ {len(ids)} IDs enviados a n8n."
            logger.info(f"{success_message} Datos enviados: {data_to_send}")
            
            return {
                "success": True, 
                "message": success_message,
                "response": response_json,
                "sent_data": data_to_send
            }
            
        except Exception as e: 
            error_message = f"❌ Error al enviar IDs a n8n: {e}"
            logger.error(error_message)
            return {"success": False, "message": error_message}
