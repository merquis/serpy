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
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        logger.info(f"Total de URLs únicas encontradas: {len(unique_urls)}")
        for i, url in enumerate(unique_urls[:3]):
            logger.info(f"URL {i+1}: {url}")
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
            
            return "Hotel"
            
        except Exception as e:
            logger.debug(f"Error extrayendo nombre del hotel de URL {url}: {e}")
            return "Hotel"
    
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
                for i, url in enumerate(urls):
                    try:
                        # Actualizar progreso
                        if progress_callback:
                            # Extraer nombre del hotel de la URL
                            hotel_name = self._extract_hotel_name_from_url(url)
                            
                            progress_info = {
                                "message": f"📍 Procesando hotel {i+1}/{len(urls)}: {hotel_name}",
                                "current_url": url,
                                "completed": i,
                                "total": len(urls),
                                "remaining": len(urls) - i - 1
                            }
                            progress_callback(progress_info)
                        
                        # Crear nueva página
                        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                        
                        # Navegar a la URL
                        await page.goto(url, wait_until="networkidle", timeout=60000)
                        
                        # Esperar un poco para asegurar que el contenido se cargue
                        await page.wait_for_timeout(3000)
                        
                        # Esperar específicamente por elementos con data-hotel-rounded-price
                        try:
                            await page.wait_for_selector('[data-hotel-rounded-price]', timeout=5000)
                            logger.info("Encontrado elemento con data-hotel-rounded-price")
                        except:
                            logger.warning("No se encontró elemento con data-hotel-rounded-price en 5 segundos")
                        
                        # Hacer scroll para cargar contenido dinámico
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        
                        # Obtener el HTML
                        html = await page.content()
                        
                        # Extraer datos de JavaScript (utag_data y dataLayer)
                        js_data = await self._extract_javascript_data(page)
                        
                        # Cerrar la página
                        await page.close()
                        
                        # Parsear el HTML
                        soup = BeautifulSoup(html, "html.parser")
                        hotel_data = self._parse_hotel_html(soup, url, js_data)
                        hotel_data["method"] = "rebrowser-playwright"
                        results.append(hotel_data)
                        
                    except Exception as e:
                        logger.error(f"Error procesando {url}: {e}")
                        results.append({
                            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "busqueda_checkin": "",
                            "busqueda_checkout": "",
                            "busqueda_adultos": "",
                            "busqueda_ninos": "",
                            "busqueda_habitaciones": "",
                            "nombre_alojamiento": "",
                            "tipo_alojamiento": "",
                            "direccion": "",
                            "codigo_postal": "",
                            "ciudad": "",
                            "pais": "",
                            "valoracion_global": "",
                            "numero_opiniones": "",
                            "estrellas": "",
                            "rango_precios": "",
                            "url_original": url,
                            "error": "Error de procesamiento",
                            "details": str(e),
                            "method": "rebrowser-playwright"
                        })
                
                # Actualizar progreso final
                if progress_callback:
                    progress_info = {
                        "message": f"Completado: {len(urls)} URLs procesadas",
                        "completed": len(urls),
                        "total": len(urls),
                        "remaining": 0
                    }
                    progress_callback(progress_info)
                    
            finally:
                await browser.close()
        
        return results
    
    
    async def _extract_javascript_data(self, page) -> Dict[str, Any]:
        """
        Extrae datos de window.utag_data, window.dataLayer y busca formattedAddress
        
        Args:
            page: Página de Playwright
            
        Returns:
            Diccionario con datos extraídos del JavaScript
        """
        js_data = {}
        
        try:
            # Extraer window.utag_data
            utag_data = await page.evaluate("() => window.utag_data || {}")
            if utag_data:
                js_data["utag_data"] = utag_data
                logger.debug(f"Extraídos datos de utag_data: {len(utag_data)} campos")
            
            # Extraer window.dataLayer
            data_layer = await page.evaluate("() => window.dataLayer || []")
            if data_layer and len(data_layer) > 0:
                # Tomar el primer elemento del dataLayer que suele contiene los datos del hotel
                js_data["dataLayer"] = data_layer[0] if isinstance(data_layer, list) else data_layer
                logger.debug(f"Extraídos datos de dataLayer: {len(js_data['dataLayer'])} campos")
            
            # Buscar formattedAddress en diferentes lugares del DOM/JavaScript
            formatted_address = await self._search_formatted_address(page)
            if formatted_address:
                js_data["formattedAddress"] = formatted_address
                logger.debug(f"Encontrado formattedAddress: {formatted_address}")
            
            # Buscar reviewsCount en script data-capla-application-context
            reviews_count = await self._search_reviews_count(page)
            if reviews_count:
                js_data["reviewsCount"] = reviews_count
                logger.debug(f"Encontrado reviewsCount: {reviews_count}")
            
            # Buscar precio medio por noche
            average_price = await self._search_average_price(page)
            if average_price:
                js_data["averagePrice"] = average_price
                logger.debug(f"Encontrado precio medio: {average_price}")
            
        except Exception as e:
            logger.error(f"Error extrayendo datos de JavaScript: {e}")
        
        return js_data
    
    async def _search_formatted_address(self, page) -> str:
        """
        Busca el campo formattedAddress en diferentes lugares del DOM y JavaScript
        
        Args:
            page: Página de Playwright
            
        Returns:
            Dirección formateada si se encuentra, cadena vacía si no
        """
        try:
            # Buscar en scripts JSON-LD y data-capla-application-context
            formatted_address = await page.evaluate("""
                () => {
                    // Función auxiliar para buscar formattedAddress en un objeto recursivamente
                    function findFormattedAddress(obj, maxDepth = 5, currentDepth = 0) {
                        if (currentDepth > maxDepth || !obj || typeof obj !== 'object') return null;
                        
                        if (obj.formattedAddress && typeof obj.formattedAddress === 'string') {
                            return obj.formattedAddress;
                        }
                        
                        if (obj.address && obj.address.formattedAddress) {
                            return obj.address.formattedAddress;
                        }
                        
                        // Buscar recursivamente en propiedades del objeto
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
                    
                    // 1. Buscar en script data-capla-application-context (PRIORIDAD ALTA)
                    const caplaScript = document.querySelector('script[data-capla-application-context]');
                    if (caplaScript && caplaScript.textContent) {
                        try {
                            const caplaData = JSON.parse(caplaScript.textContent);
                            const result = findFormattedAddress(caplaData);
                            if (result) return result;
                        } catch (e) {}
                    }
                    
                    // 2. Buscar en scripts JSON-LD
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (let script of scripts) {
                        try {
                            const data = JSON.parse(script.textContent);
                            const result = findFormattedAddress(data);
                            if (result) return result;
                        } catch (e) {}
                    }
                    
                    // 3. Buscar en todos los scripts type="application/json"
                    const jsonScripts = document.querySelectorAll('script[type="application/json"]');
                    for (let script of jsonScripts) {
                        try {
                            const data = JSON.parse(script.textContent);
                            const result = findFormattedAddress(data);
                            if (result) return result;
                        } catch (e) {}
                    }
                    
                    // 4. Buscar en window.__INITIAL_STATE__ o similares
                    if (window.__INITIAL_STATE__) {
                        const result = findFormattedAddress(window.__INITIAL_STATE__);
                        if (result) return result;
                    }
                    
                    // 5. Buscar en window.b_hotel_data o similares
                    if (window.b_hotel_data) {
                        const result = findFormattedAddress(window.b_hotel_data);
                        if (result) return result;
                    }
                    
                    // 6. Buscar en todos los objetos window que contengan formattedAddress
                    for (let key in window) {
                        try {
                            if (typeof window[key] === 'object' && window[key] !== null) {
                                const result = findFormattedAddress(window[key], 3); // Menor profundidad para window objects
                                if (result) return result;
                            }
                        } catch (e) {}
                    }
                    
                    return '';
                }
            """)
            
            if formatted_address:
                return formatted_address
            
            # Buscar en el HTML usando selectores específicos
            address_selectors = [
                '[data-testid="address"]',
                '.hp_address_subtitle',
                '.hp-hotel-address',
                '.address',
                '[class*="address"]',
                '[data-address]'
            ]
            
            for selector in address_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and len(text.strip()) > 10:  # Dirección debe tener cierta longitud
                            return text.strip()
                except:
                    continue
            
            return ""
            
        except Exception as e:
            logger.error(f"Error buscando reviewsCount: {e}")
            return ""
    
    def _calculate_nights_from_url(self, url: str) -> Optional[int]:
        """
        Calcula el número de noches desde las fechas en la URL
        
        Args:
            url: URL del hotel con parámetros de búsqueda
            
        Returns:
            Número de noches o None si no se puede calcular
        """
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            checkin_str = query_params.get('checkin', [''])[0]
            checkout_str = query_params.get('checkout', [''])[0]
            
            if checkin_str and checkout_str:
                checkin = datetime.datetime.strptime(checkin_str, '%Y-%m-%d')
                checkout = datetime.datetime.strptime(checkout_str, '%Y-%m-%d')
                nights = (checkout - checkin).days
                if nights > 0:
                    return nights
        except Exception as e:
            logger.debug(f"Error calculando noches desde URL: {e}")
        
        return None
    
    async def _search_average_price(self, page) -> str:
        """
        Busca el precio medio por noche en diferentes lugares del DOM y JavaScript
        Calcula el precio por noche dividiendo el precio total entre el número de noches
        
        Args:
            page: Página de Playwright
            
        Returns:
            Precio medio por noche si se encuentra, cadena vacía si no
        """
        try:
            # Primero, intentar calcular las noches desde la URL
            current_url = page.url
            nights_from_url = self._calculate_nights_from_url(current_url)
            
            # Buscar precio total y número de noches para calcular precio por noche
            price_info = await page.evaluate("""
                () => {
                    console.log('=== INICIANDO BÚSQUEDA DE PRECIO ===');
                    
                    // Variables para almacenar resultados
                    let nights = """ + str(nights_from_url if nights_from_url else 'null') + """;
                    let totalPrice = null;
                    let debugInfo = [];
                    
                    // Si ya tenemos noches desde la URL, registrarlo
                    if (nights) {
                        debugInfo.push(`Noches desde URL: ${nights}`);
                    }
                    
                    // 1. BUSCAR NÚMERO DE NOCHES - MÁS EXHAUSTIVO
                    debugInfo.push('Buscando número de noches...');
                    
                    // Buscar en todos los elementos del DOM
                    const allElements = document.querySelectorAll('*');
                    for (let element of allElements) {
                        const text = element.textContent || element.innerText || '';
                        
                        // Patrones más específicos para noches
                        const nightPatterns = [
                            /precio\s+para\s+(\d+)\s+noches?/i,
                            /price\s+for\s+(\d+)\s+nights?/i,
                            /para\s+(\d+)\s+noches?/i,
                            /for\s+(\d+)\s+nights?/i,
                            /(\d+)\s+noches?\s+/i,
                            /(\d+)\s+nights?\s+/i,
                            /\s+(\d+)\s+noches/i,
                            /\s+(\d+)\s+nights/i
                        ];
                        
                        for (let pattern of nightPatterns) {
                            const match = text.match(pattern);
                            if (match && match[1]) {
                                const foundNights = parseInt(match[1]);
                                if (foundNights > 0 && foundNights < 100) { // Validar rango razonable
                                    nights = foundNights;
                                    debugInfo.push(`Noches encontradas: ${nights} en texto: "${text.substring(0, 100)}..."`);
                                    break;
                                }
                            }
                        }
                        if (nights) break;
                    }
                    
                    // Si no encontramos noches, buscar en atributos data
                    if (!nights) {
                        const elementsWithData = document.querySelectorAll('[data-*]');
                        for (let element of elementsWithData) {
                            for (let attr of element.attributes) {
                                if (attr.name.startsWith('data-') && attr.value) {
                                    const nightMatch = attr.value.match(/(\d+)\s*nights?/i);
                                    if (nightMatch) {
                                        nights = parseInt(nightMatch[1]);
                                        debugInfo.push(`Noches encontradas en atributo ${attr.name}: ${nights}`);
                                        break;
                                    }
                                }
                            }
                            if (nights) break;
                        }
                    }
                    
                    // 2. BUSCAR PRECIO TOTAL - Buscar el script después de application/ld+json
                    debugInfo.push('Buscando script con b_rooms_available_and_soldout después de JSON-LD...');
                    
                    let rawPrices = [];
                    
                    // Buscar todos los scripts JSON-LD
                    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
                    debugInfo.push(`Scripts JSON-LD encontrados: ${jsonLdScripts.length}`);
                    
                    // Para cada script JSON-LD, buscar el siguiente script
                    for (let jsonLdScript of jsonLdScripts) {
                        let nextElement = jsonLdScript.nextElementSibling;
                        
                        // Buscar el siguiente script (puede haber otros elementos en medio)
                        while (nextElement && nextElement.tagName !== 'SCRIPT') {
                            nextElement = nextElement.nextElementSibling;
                        }
                        
                        if (nextElement && nextElement.tagName === 'SCRIPT' && nextElement.textContent) {
                            // Verificar si este script contiene b_rooms_available_and_soldout
                            if (nextElement.textContent.includes('b_rooms_available_and_soldout:')) {
                                debugInfo.push('¡Encontrado script con b_rooms_available_and_soldout después de JSON-LD!');
                                
                                // Buscar todos los b_raw_price en este script
                                const scriptContent = nextElement.textContent;
                                const rawPriceRegex = /"b_raw_price"\s*:\s*"([0-9]+(?:\.[0-9]+)?)"/g;
                                let match;
                                
                                while ((match = rawPriceRegex.exec(scriptContent)) !== null) {
                                    const price = parseFloat(match[1]);
                                    if (!isNaN(price) && price > 0) {
                                        rawPrices.push(price);
                                        debugInfo.push(`b_raw_price encontrado: ${price}`);
                                    }
                                }
                                
                                break; // Ya encontramos el script correcto
                            }
                        }
                    }
                    
                    // Si no encontramos con el método anterior, buscar en todo el HTML como fallback
                    if (rawPrices.length === 0) {
                        debugInfo.push('No se encontró con método JSON-LD, buscando en todo el DOM...');
                        
                        const allHTML = document.documentElement.innerHTML;
                        const startIndex = allHTML.indexOf('b_rooms_available_and_soldout: [');
                        
                        if (startIndex !== -1) {
                            debugInfo.push('Encontrado b_rooms_available_and_soldout: [ en el DOM (fallback)');
                            const contentAfterArray = allHTML.substring(startIndex, startIndex + 50000);
                            const rawPriceRegex = /"b_raw_price"\s*:\s*"([0-9]+(?:\.[0-9]+)?)"/g;
                            let match;
                            
                            while ((match = rawPriceRegex.exec(contentAfterArray)) !== null) {
                                const price = parseFloat(match[1]);
                                if (!isNaN(price) && price > 0) {
                                    rawPrices.push(price);
                                    debugInfo.push(`b_raw_price encontrado (fallback): ${price}`);
                                }
                            }
                        }
                    }
                    
                    debugInfo.push(`Total de b_raw_price encontrados: ${rawPrices.length}`);
                    
                    // Si encontramos precios, usar el más pequeño y redondearlo
                    if (rawPrices.length > 0) {
                        const minPrice = Math.min(...rawPrices);
                        totalPrice = Math.floor(minPrice); // Redondear hacia abajo (eliminar decimales)
                        debugInfo.push(`Precio más pequeño seleccionado y redondeado: ${totalPrice} (original: ${minPrice})`);
                    }
                    
                    // Si no encontramos b_raw_price, buscar data-hotel-rounded-price como fallback
                    if (!totalPrice) {
                        debugInfo.push('No se encontró b_raw_price, buscando data-hotel-rounded-price...');
                        let roundedPrices = [];
                    
                    // Función para buscar recursivamente en todo el DOM
                    function searchForRoundedPrice(element) {
                        // Verificar si el elemento tiene el atributo
                        if (element.hasAttribute && element.hasAttribute('data-hotel-rounded-price')) {
                            const priceValue = element.getAttribute('data-hotel-rounded-price');
                            if (priceValue) {
                                const price = parseFloat(priceValue);
                                if (!isNaN(price) && price > 0) {
                                    roundedPrices.push({
                                        price: price,
                                        element: element.tagName,
                                        classes: element.className,
                                        id: element.id
                                    });
                                }
                            }
                        }
                        
                        // Buscar en todos los hijos
                        if (element.children) {
                            for (let child of element.children) {
                                searchForRoundedPrice(child);
                            }
                        }
                    }
                    
                    // Buscar en todo el documento
                    debugInfo.push(`Iniciando búsqueda profunda de data-hotel-rounded-price...`);
                    searchForRoundedPrice(document.documentElement);
                    
                    debugInfo.push(`Total de elementos con data-hotel-rounded-price encontrados: ${roundedPrices.length}`);
                    
                    // Mostrar todos los precios encontrados
                    for (let priceInfo of roundedPrices) {
                        debugInfo.push(`Encontrado: ${priceInfo.price} en <${priceInfo.element}> class="${priceInfo.classes}" id="${priceInfo.id}"`);
                    }
                    
                    // También buscar con querySelector para verificar
                    const queryResults = document.querySelectorAll('[data-hotel-rounded-price]');
                    debugInfo.push(`Verificación con querySelectorAll: ${queryResults.length} elementos`);
                    
                    // Buscar específicamente en tablas
                    const tables = document.querySelectorAll('table');
                    debugInfo.push(`Tablas encontradas: ${tables.length}`);
                    
                    for (let table of tables) {
                        const trs = table.querySelectorAll('tr[data-hotel-rounded-price]');
                        if (trs.length > 0) {
                            debugInfo.push(`Tabla con TRs con data-hotel-rounded-price: ${trs.length} filas`);
                        }
                    }
                    
                    // Buscar en el HTML como texto para verificar si existe
                    const htmlText = document.documentElement.outerHTML;
                    const dataHotelMatches = htmlText.match(/data-hotel-rounded-price="(\d+)"/g);
                    if (dataHotelMatches) {
                        debugInfo.push(`Encontrado en HTML como texto: ${dataHotelMatches.length} coincidencias`);
                        for (let match of dataHotelMatches.slice(0, 5)) { // Mostrar primeras 5
                            debugInfo.push(`  - ${match}`);
                        }
                            'span.prco-valign-middle-helper',
                            // Selectores de precios en tablas
                            'td.hprt-table-cell-price',
                            'div.hprt-price-price',
                            'span.hprt-price-price-actual',
                            '.bui-price-display__value--prco',
                            // Selectores genéricos
                            '[class*="price"]',
                            '[data-testid*="price"]',
                            '[data-et-mousecenter*="price"]',
                            '[data-et-mouseenter*="price"]',
                            'span[data-et-mousecenter]',
                            'span[data-et-mouseenter]',
                            'td[class*="price"]',
                            'div[class*="price"]',
                            'span[class*="price"]',
                            // Selectores de tabla
                            'td',
                            'th',
                            '.e2e-hprt-table-cell',
                            // Otros posibles
                            '.totalPrice',
                            '.total-price',
                            '.price-total',
                            '.amount'
                        ];
                        
                        // Array para almacenar todos los precios encontrados
                        let foundPrices = [];
                        
                        for (let selector of priceSelectors) {
                            try {
                                const elements = document.querySelectorAll(selector);
                                for (let element of elements) {
                                    // Obtener texto visible
                                    const text = element.textContent || element.innerText || '';
                                    
                                    // Si el elemento no es visible, saltar
                                    const style = window.getComputedStyle(element);
                                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                                    
                                    // Buscar precios con diferentes formatos
                                    const pricePatterns = [
                                        /€\s*([1-9]\d{0,4}(?:[.,]\d{1,3})?)/g,  // €1.473 o €1,473
                                        /([1-9]\d{0,4}(?:[.,]\d{1,3})?)\s*€/g,  // 1.473€ o 1,473€
                                        /EUR\s*([1-9]\d{0,4}(?:[.,]\d{1,3})?)/gi, // EUR 1.473
                                        /([1-9]\d{0,4}(?:[.,]\d{1,3})?)\s*EUR/gi, // 1.473 EUR
                                    ];
                                    
                                    for (let pattern of pricePatterns) {
                                        let match;
                                        while ((match = pattern.exec(text)) !== null) {
                                            // Normalizar el precio (quitar puntos de miles, cambiar coma por punto)
                                            let priceStr = match[1].replace(/\./g, '').replace(',', '.');
                                            const price = parseFloat(priceStr);
                                            
                                            // Validar rango de precio razonable
                                            if (price >= 20 && price <= 10000) {
                                                foundPrices.push({
                                                    price: price,
                                                    element: element.tagName,
                                                    selector: selector,
                                                    text: text.substring(0, 100)
                                                });
                                            }
                                        }
                                    }
                                }
                            } catch (e) {
                                debugInfo.push(`Error con selector ${selector}: ${e.message}`);
                            }
                        }
                        
                        // Ordenar precios encontrados por valor (de mayor a menor)
                        foundPrices.sort((a, b) => b.price - a.price);
                        debugInfo.push(`Precios encontrados: ${foundPrices.length}`);
                        
                        // Si tenemos noches, buscar el precio que mejor se ajuste
                        if (nights && foundPrices.length > 0) {
                            // El precio total suele ser uno de los más altos
                            for (let priceInfo of foundPrices) {
                                // Verificar si es un precio razonable para el número de noches
                                const pricePerNight = priceInfo.price / nights;
                                if (pricePerNight >= 20 && pricePerNight <= 2000) {
                                    totalPrice = priceInfo.price;
                                    debugInfo.push(`Precio seleccionado: ${totalPrice} (${priceInfo.text})`);
                                    break;
                                }
                            }
                        }
                        
                        // Si no tenemos precio aún, tomar el precio más alto encontrado
                        if (!totalPrice && foundPrices.length > 0) {
                            totalPrice = foundPrices[0].price;
                            debugInfo.push(`Precio más alto seleccionado: ${totalPrice}`);
                        }
                    }
                    
                    // 3. BUSCAR EN DATOS DE JAVASCRIPT
                    if (!totalPrice || !nights) {
                        debugInfo.push('Buscando en datos JavaScript...');
                        
                        // Buscar en window.utag_data
                        if (window.utag_data) {
                            if (!nights && window.utag_data.nights) {
                                nights = parseInt(window.utag_data.nights);
                                debugInfo.push(`Noches desde utag_data: ${nights}`);
                            }
                            if (!totalPrice && window.utag_data.ttv) {
                                totalPrice = parseFloat(window.utag_data.ttv);
                                debugInfo.push(`Precio desde utag_data.ttv: ${totalPrice}`);
                            }
                        }
                        
                        // Buscar en window.dataLayer
                        if (window.dataLayer && Array.isArray(window.dataLayer)) {
                            for (let layer of window.dataLayer) {
                                if (!nights && layer.nights) {
                                    nights = parseInt(layer.nights);
                                    debugInfo.push(`Noches desde dataLayer: ${nights}`);
                                }
                                if (!totalPrice && layer.ttv) {
                                    totalPrice = parseFloat(layer.ttv);
                                    debugInfo.push(`Precio desde dataLayer.ttv: ${totalPrice}`);
                                }
                            }
                        }
                    }
                    
                    // 4. BÚSQUEDA ALTERNATIVA - Buscar "Precio para X noches" directamente
                    if (!totalPrice && nights) {
                        debugInfo.push('Búsqueda alternativa: buscando "Precio para X noches"...');
                        
                        // Buscar elementos que contengan "Precio para" y un número
                        const allTextElements = document.querySelectorAll('*');
                        for (let element of allTextElements) {
                            const text = element.textContent || element.innerText || '';
                            
                            // Buscar patrón "Precio para X noches" seguido de un precio
                            const precioParaNochesMatch = text.match(/precio\s+para\s+\d+\s+noches?[^€]*€\s*([1-9]\d{0,4}(?:[.,]\d{1,3})?)/i);
                            if (precioParaNochesMatch) {
                                const priceStr = precioParaNochesMatch[1].replace(/\./g, '').replace(',', '.');
                                const price = parseFloat(priceStr);
                                if (price >= 100 && price <= 10000) {
                                    totalPrice = price;
                                    debugInfo.push(`Precio encontrado con patrón "Precio para X noches": ${totalPrice}`);
                                    break;
                                }
                            }
                        }
                    }
                    
                    // 5. ÚLTIMA BÚSQUEDA - Buscar cualquier precio grande que podría ser el total
                    if (!totalPrice && nights) {
                        debugInfo.push('Última búsqueda: buscando cualquier precio grande...');
                        
                        // Buscar todos los precios en la página
                        const allPrices = [];
                        const priceRegex = /€\s*([1-9]\d{2,4}(?:[.,]\d{1,3})?)/g;
                        const bodyText = document.body.textContent || document.body.innerText || '';
                        
                        let match;
                        while ((match = priceRegex.exec(bodyText)) !== null) {
                            const priceStr = match[1].replace(/\./g, '').replace(',', '.');
                            const price = parseFloat(priceStr);
                            if (price >= 100 && price <= 10000) {
                                allPrices.push(price);
                            }
                        }
                        
                        // Ordenar precios de mayor a menor
                        allPrices.sort((a, b) => b - a);
                        
                        // Buscar un precio que tenga sentido para el número de noches
                        for (let price of allPrices) {
                            const pricePerNight = price / nights;
                            if (pricePerNight >= 30 && pricePerNight <= 1000) {
                                totalPrice = price;
                                debugInfo.push(`Precio probable encontrado: ${totalPrice} (${pricePerNight} EUR/noche)`);
                                break;
                            }
                        }
                    }
                    
                    // 6. DEVOLVER PRECIO TOTAL SIN DIVIDIR (PARA DEBUG)
                    console.log('Debug info:', debugInfo);
                    console.log(`Noches: ${nights}, Precio total: ${totalPrice}`);
                    
                    // TEMPORAL: Devolver precio total sin dividir para ver qué estamos capturando
                    if (totalPrice) {
                        console.log(`Precio total encontrado (sin dividir): ${totalPrice}`);
                        return totalPrice.toString() + ' EUR (total sin dividir)';
                    }
                    
                    console.log('No se encontró precio');
                    return '';
                }
            """)
            
            logger.debug(f"Resultado de búsqueda de precio: {price_info}")
            return price_info if price_info else ""
            
        except Exception as e:
            logger.error(f"Error buscando precio medio: {e}")
            return ""
    
    async def _search_reviews_count(self, page) -> str:
        """
        Busca el número de opiniones en diferentes lugares del DOM y JavaScript
        
        Args:
            page: Página de Playwright
            
        Returns:
            Número de reviews si se encuentra, cadena vacía si no
        """
        try:
            # Buscar reviewsCount en script data-capla-application-context y showReviews
            reviews_count = await page.evaluate("""
                () => {
                    // Función auxiliar para buscar reviewsCount en un objeto recursivamente
                    function findReviewsCount(obj, maxDepth = 5, currentDepth = 0) {
                        if (currentDepth > maxDepth || !obj || typeof obj !== 'object') return null;
                        
                        // Buscar reviewsCount directamente
                        if (obj.reviewsCount !== undefined && obj.reviewsCount !== null) {
                            return obj.reviewsCount.toString();
                        }
                        
                        // Buscar en propiedades anidadas
                        for (let key in obj) {
                            try {
                                if (typeof obj[key] === 'object' && obj[key] !== null) {
                                    const result = findReviewsCount(obj[key], maxDepth, currentDepth + 1);
                                    if (result) return result;
                                }
                            } catch (e) {}
                        }
                        
                        return null;
                    }
                    
                    // 1. Buscar patrón showReviews: parseInt("....", ...) en todos los scripts
                    const allScripts = document.querySelectorAll('script');
                    for (let script of allScripts) {
                        if (script.textContent) {
                            // Buscar patrón showReviews: parseInt("número", cualquier_cosa)
                            const showReviewsMatch = script.textContent.match(/showReviews:\s*parseInt\s*\(\s*["'](\d+)["']\s*,\s*[^)]+\)/);
                            if (showReviewsMatch && showReviewsMatch[1]) {
                                return showReviewsMatch[1];
                            }
                            
                            // Buscar patrón alternativo showReviews: parseInt(número, cualquier_cosa)
                            const showReviewsMatch2 = script.textContent.match(/showReviews:\s*parseInt\s*\(\s*(\d+)\s*,\s*[^)]+\)/);
                            if (showReviewsMatch2 && showReviewsMatch2[1]) {
                                return showReviewsMatch2[1];
                            }
                            
                            // Buscar patrón más general showReviews: parseInt("número")
                            const showReviewsMatch3 = script.textContent.match(/showReviews:\s*parseInt\s*\(\s*["'](\d+)["']\s*\)/);
                            if (showReviewsMatch3 && showReviewsMatch3[1]) {
                                return showReviewsMatch3[1];
                            }
                            
                            // Buscar patrón más general showReviews: parseInt(número)
                            const showReviewsMatch4 = script.textContent.match(/showReviews:\s*parseInt\s*\(\s*(\d+)\s*\)/);
                            if (showReviewsMatch4 && showReviewsMatch4[1]) {
                                return showReviewsMatch4[1];
                            }
                        }
                    }
                    
                    // 2. Buscar en script data-capla-application-context
                    const caplaScript = document.querySelector('script[data-capla-application-context]');
                    if (caplaScript && caplaScript.textContent) {
                        try {
                            const caplaData = JSON.parse(caplaScript.textContent);
                            const result = findReviewsCount(caplaData);
                            if (result) return result;
                        } catch (e) {
                            console.error('Error parsing capla script:', e);
                        }
                    }
                    
                    return '';
                }
            """)
            
            return reviews_count if reviews_count else ""
            
        except Exception as e:
            logger.error(f"Error buscando reviewsCount: {e}")
            return ""
    
    def _extract_postal_code_from_address(self, address: str) -> str:
        """
        Extrae el código postal de una dirección formateada
        
        Args:
            address: Dirección completa (ej: "Roque Nublo, 1, 38660 Adeje, España")
            
        Returns:
            Código postal extraído o cadena vacía si no se encuentra
        """
        if not address:
            return ""
        
        try:
            # Buscar números de 4-5 dígitos (códigos postales típicos)
            # Priorizar números de 5 dígitos, luego 4 dígitos
            import re
            
            # Buscar códigos postales de 5 dígitos
            postal_5_digits = re.findall(r'\b\d{5}\b', address)
            if postal_5_digits:
                return postal_5_digits[0]  # Tomar el primero encontrado
            
            # Si no hay de 5 dígitos, buscar de 4 dígitos
            postal_4_digits = re.findall(r'\b\d{4}\b', address)
            if postal_4_digits:
                return postal_4_digits[0]  # Tomar el primero encontrado
            
            return ""
            
        except Exception as e:
            logger.debug(f"Error extrayendo código postal de dirección '{address}': {e}")
            return ""
    
    def _calculate_price_per_night(self, price_info: str, nights: Optional[int]) -> str:
        """
        Calcula el precio por noche si el precio_info contiene un precio total
        
        Args:
            price_info: String con información de precio (ej: "1473 EUR")
            nights: Número de noches
            
        Returns:
            Precio por noche calculado o el precio original si no se puede calcular
        """
        if not price_info or not nights or nights <= 0:
            return price_info or ""
        
        try:
            # Extraer el número del precio
            import re
            price_match = re.search(r'(\d+(?:[.,]\d+)?)', price_info)
            if price_match:
                # Normalizar el precio (cambiar coma por punto)
                price_str = price_match.group(1).replace(',', '.')
                total_price = float(price_str)
                
                # Calcular precio por noche
                price_per_night = round(total_price / nights, 2)
                
                # Devolver en el mismo formato
                return f"{price_per_night} EUR por noche"
            
            return price_info
            
        except Exception as e:
            logger.debug(f"Error calculando precio por noche: {e}")
            return price_info or ""
    
    def _parse_hotel_html(self, soup: BeautifulSoup, url: str, js_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Parsea el HTML de la página del hotel y combina con datos de JavaScript"""
        # Extraer parámetros de la URL
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Parámetros de búsqueda
        group_adults = query_params.get('group_adults', [''])[0]
        group_children = query_params.get('group_children', [''])[0]
        no_rooms = query_params.get('no_rooms', [''])[0]
        checkin = query_params.get('checkin', [''])[0]
        checkout = query_params.get('checkout', [''])[0]
        
        # Calcular número de noches desde checkin y checkout
        nights = None
        if checkin and checkout:
            try:
                checkin_date = datetime.datetime.strptime(checkin, '%Y-%m-%d')
                checkout_date = datetime.datetime.strptime(checkout, '%Y-%m-%d')
                nights = (checkout_date - checkin_date).days
            except Exception as e:
                logger.debug(f"Error calculando noches: {e}")
        
        # Extraer datos estructurados
        data_extraida = self._extract_structured_data(soup)
        
        # Extraer imágenes
        imagenes = self._extract_images(soup)
        
        # Extraer servicios
        servicios = self._extract_facilities(soup)
        
        # Extraer título y subtítulos
        titulo_h1 = ""
        h1_tag = soup.find("h1")
        if h1_tag:
            titulo_h1 = h1_tag.get_text(strip=True)
        elif data_extraida:
            titulo_h1 = data_extraida.get("name", "")
        
        h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2") if h2.get_text(strip=True)]
        
        # Construir resultado
        address_info = data_extraida.get("address", {}) if data_extraida else {}
        rating_info = data_extraida.get("aggregateRating", {}) if data_extraida else {}
        
        # Extraer datos de JavaScript si están disponibles
        js_utag_data = js_data.get("utag_data", {}) if js_data else {}
        js_data_layer = js_data.get("dataLayer", {}) if js_data else {}
        
        # Función auxiliar para obtener valor con prioridad: JS -> HTML -> fallback
        def get_best_value(js_key_utag, js_key_layer, html_value, fallback=""):
            # Prioridad: utag_data -> dataLayer -> HTML -> fallback
            if js_utag_data.get(js_key_utag):
                return js_utag_data.get(js_key_utag)
            elif js_data_layer.get(js_key_layer):
                return js_data_layer.get(js_key_layer)
            elif html_value:
                return html_value
            else:
                return fallback
        
        # Calcular precio por noche
        average_price = js_data.get("averagePrice", "")
        price_per_night = self._calculate_price_per_night(average_price, nights)
        price_range_fallback = data_extraida.get("priceRange", "") if data_extraida else ""
        final_price = price_per_night or price_range_fallback or ""
        
        # Log para depuración
        logger.info(f"DEBUG PRECIO - averagePrice: {average_price}, nights: {nights}, price_per_night: {price_per_night}, final: {final_price}")
        
        return {
            # Campos principales al inicio
            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "busqueda_checkin": checkin,
            "busqueda_checkout": checkout,
            "busqueda_adultos": group_adults,
            "busqueda_ninos": group_children,
            "busqueda_habitaciones": no_rooms,
            "nombre_alojamiento": get_best_value(
                "hotel_name", "hotel_name", 
                data_extraida.get("name", titulo_h1) if data_extraida else titulo_h1
            ),
            "tipo_alojamiento": data_extraida.get("@type", "Hotel") if data_extraida else "Hotel",
            "direccion": js_data.get("formattedAddress") or get_best_value(
                "formattedAddress", "formattedAddress",
                address_info.get("streetAddress")
            ),
            "codigo_postal": self._extract_postal_code_from_address(
                js_data.get("formattedAddress") or get_best_value(
                    "formattedAddress", "formattedAddress",
                    address_info.get("streetAddress")
                )
            ) or address_info.get("postalCode"),
            "ciudad": get_best_value(
                "city_name", "city_name",
                address_info.get("addressLocality")
            ),
            "pais": get_best_value(
                "country_name", "country_name",
                address_info.get("addressCountry")
            ),
            "valoracion_global": get_best_value(
                "utrs", "utrs",
                rating_info.get("ratingValue")
            ),
            "numero_opiniones": js_data.get("reviewsCount") or get_best_value(
                "reviewCount", "reviewCount",
                rating_info.get("reviewCount")
            ),
            "estrellas": get_best_value(
                "hotel_class", "hotel_class",
                ""
            ),
            "rango_precios": final_price,
            # URLs y otros campos después
            "url_original": url,
            "url_hotel_booking": data_extraida.get("url") if data_extraida else url,
            "descripcion_corta": data_extraida.get("description") if data_extraida else "",
            "titulo_h1": titulo_h1,
            "subtitulos_h2": h2s,
            "servicios_principales": servicios,
            "imagenes": imagenes
        }
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrae datos estructurados JSON-LD"""
        try:
            scripts_ldjson = soup.find_all('script', type='application/ld+json')
            for script in scripts_ldjson:
                if script.string:
                    try:
                        data_json = json.loads(script.string)
                        if isinstance(data_json, dict) and data_json.get("@type") == "Hotel":
                            return data_json
                    except:
                        continue
        except:
            pass
        return {}
    
    def _extract_images(self, soup: BeautifulSoup, max_images: int = 15) -> List[str]:
        """Extrae URLs de imágenes del hotel"""
        imagenes = []
        found_urls = set()
        
        try:
            for img_tag in soup.find_all("img"):
                src = img_tag.get("src")
                if (src and 
                    src.startswith("https://cf.bstatic.com/xdata/images/hotel/") and 
                    ".jpg" in src and 
                    src not in found_urls and
                    len(imagenes) < max_images):
                    
                    # Ajustar tamaño de imagen
                    if "/max1024x768/" not in src:
                        src = re.sub(r"/max[^/]+/", "/max1024x768/", src)
                    
                    # Quitar parámetros adicionales
                    if "&o=" in src:
                        src = src.split("&o=")[0]
                    
                    imagenes.append(src)
                    found_urls.add(src)
        except Exception as e:
            logger.error(f"Error extrayendo imágenes: {e}")
        
        return imagenes
    
    def _extract_facilities(self, soup: BeautifulSoup) -> List[str]:
        """Extrae los servicios/facilidades del hotel"""
        servicios_set = set()
        
        try:
            # Clases comunes para servicios en Booking
            possible_classes = [
                "hotel-facilities__list",
                "facilitiesChecklistSection",
                "hp_desc_important_facilities",
                "bui-list__description",
                "db29ecfbe2"
            ]
            
            for class_name in possible_classes:
                for container in soup.find_all(class_=class_name):
                    for item in container.find_all(['li', 'span', 'div'], recursive=True):
                        texto = item.get_text(strip=True)
                        if texto and len(texto) > 3:
                            servicios_set.add(texto)
        except Exception as e:
            logger.error(f"Error extrayendo servicios: {e}")
        
        return sorted(list(servicios_set))
