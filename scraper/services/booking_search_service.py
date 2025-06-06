"""
Servicio de Búsqueda en Booking - Extracción de resultados de búsqueda
"""
import json
import datetime
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode
import logging
import asyncio
from rebrowser_playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BookingSearchService:
    """Servicio para buscar y extraer resultados de búsqueda en Booking.com"""
    
    def __init__(self):
        self.base_url = "https://www.booking.com/searchresults.es.html"
    
    def build_search_url(self, params: Dict[str, Any]) -> str:
        """
        Construye la URL de búsqueda con los parámetros especificados
        
        Args:
            params: Diccionario con los parámetros de búsqueda
            
        Returns:
            URL completa de búsqueda
        """
        # Parámetros base
        query_params = {
            'ss': params.get('destination', 'Tenerife'),
            'dest_type': params.get('dest_type', 'region'),
            'dest_id': params.get('dest_id', ''),
            'checkin': params.get('checkin'),
            'checkout': params.get('checkout'),
            'group_adults': params.get('adults', 2),
            'group_children': params.get('children', 0),
            'no_rooms': params.get('rooms', 1),
        }
        
        # Añadir edades de niños si hay niños
        if params.get('children', 0) > 0 and params.get('children_ages'):
            for i, age in enumerate(params.get('children_ages', [])):
                query_params[f'age'] = age
        
        # Construir filtros nflt
        nflt_filters = []
        
        # Filtro de estrellas
        if params.get('stars'):
            for star in params.get('stars', []):
                nflt_filters.append(f'class={star}')
        
        # Filtro de puntuación
        if params.get('min_score'):
            score_map = {
                '7.0': '70',
                '8.0': '80',
                '9.0': '90'
            }
            nflt_filters.append(f'review_score={score_map.get(params.get("min_score"), "80")}')
        
        # Filtro de régimen
        if params.get('meal_plan'):
            meal_map = {
                'desayuno': '1',
                'media_pension': '4',
                'todo_incluido': '3',
                'desayuno_buffet': '9'
            }
            nflt_filters.append(f'mealplan={meal_map.get(params.get("meal_plan"), "1")}')
        
        # Añadir filtros nflt a la query
        if nflt_filters:
            query_params['nflt'] = ';'.join(nflt_filters)
        
        # Construir URL completa
        return f"{self.base_url}?{urlencode(query_params, doseq=True)}"
    
    async def search_hotels(
        self,
        search_params: Dict[str, Any],
        max_results: int = 10,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Realiza una búsqueda en Booking y extrae los resultados
        
        Args:
            search_params: Parámetros de búsqueda
            max_results: Número máximo de resultados a extraer
            progress_callback: Función callback para actualizar progreso
            
        Returns:
            Diccionario con la URL de búsqueda y los resultados
        """
        # Construir URL de búsqueda
        search_url = self.build_search_url(search_params)
        
        if progress_callback:
            progress_callback({
                "message": f"Iniciando búsqueda en Booking...",
                "current_url": search_url,
                "completed": 0,
                "total": max_results
            })
        
        results = {
            "search_url": search_url,
            "search_params": search_params,
            "fecha_busqueda": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "hotels": [],
            "total_found": 0,
            "extracted": 0
        }
        
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
                page = await browser.new_page(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                # Navegar a la URL de búsqueda
                await page.goto(search_url, wait_until="networkidle", timeout=60000)
                
                # Esperar a que se carguen los resultados
                await page.wait_for_timeout(5000)
                
                # Intentar cerrar posibles popups
                try:
                    close_buttons = await page.query_selector_all('[aria-label="Cerrar"], [aria-label="Dismiss sign-in info."], button[aria-label="Dismiss sign in information."]')
                    for button in close_buttons:
                        try:
                            await button.click()
                            await page.wait_for_timeout(500)
                        except:
                            pass
                except:
                    pass
                
                # Scroll para cargar más resultados
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await page.wait_for_timeout(2000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                
                # Obtener el HTML actualizado
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                # Log para depuración
                logger.info(f"URL de búsqueda: {search_url}")
                
                # Verificar si hay resultados
                no_results = soup.find(text=re.compile('No hemos encontrado|No se encontraron|0 propiedades', re.I))
                if no_results:
                    logger.warning("No se encontraron resultados en la búsqueda")
                
                # Extraer hoteles
                hotels = await self._extract_hotels_from_search(page, soup, max_results, progress_callback)
                
                # Si no tenemos suficientes hoteles, intentar cargar más
                if len(hotels) < max_results:
                    # Buscar botón de "Mostrar más resultados" o similar
                    try:
                        load_more = await page.query_selector('button[data-testid="pagination-next"], button:has-text("Mostrar más"), a.bui-pagination__link--next')
                        if load_more:
                            await load_more.click()
                            await page.wait_for_timeout(3000)
                            html = await page.content()
                            soup = BeautifulSoup(html, "html.parser")
                            additional_hotels = await self._extract_hotels_from_search(page, soup, max_results - len(hotels), progress_callback, existing_urls=set(h['url'] for h in hotels if h.get('url')))
                            hotels.extend(additional_hotels)
                    except:
                        pass
                
                results["hotels"] = hotels
                results["total_found"] = len(hotels)
                results["extracted"] = len(hotels)
                
                if progress_callback:
                    progress_callback({
                        "message": f"Búsqueda completada: {len(hotels)} hoteles encontrados",
                        "completed": len(hotels),
                        "total": max_results
                    })
                
            except Exception as e:
                logger.error(f"Error durante la búsqueda: {e}")
                results["error"] = str(e)
            finally:
                await browser.close()
        
        return results
    
    async def _extract_hotels_from_search(
        self,
        page,
        soup: BeautifulSoup,
        max_results: int,
        progress_callback: Optional[callable] = None,
        existing_urls: set = None
    ) -> List[Dict[str, Any]]:
        """Extrae información de hoteles de los resultados de búsqueda"""
        hotels = []
        seen_urls = existing_urls if existing_urls else set()  # Para evitar duplicados
        
        try:
            # ESTRATEGIA MEJORADA: Buscar h3 con <a href> justo debajo
            hotel_containers = []
            seen_urls = set()
            
            # Buscar todos los h3 en el DOM completo
            h3_elements = soup.find_all('h3')
            logger.info(f"Encontrados {len(h3_elements)} elementos h3")
            
            for h3 in h3_elements:
                # Buscar el enlace de hotel más cercano
                link = None
                
                # Estrategia 1: Buscar dentro del h3
                link = h3.find('a', href=re.compile('/hotel/'))
                
                # Estrategia 2: Buscar en el siguiente hermano
                if not link:
                    next_sibling = h3.find_next_sibling()
                    if next_sibling:
                        if next_sibling.name == 'a' and next_sibling.get('href', '').startswith('/hotel/'):
                            link = next_sibling
                        else:
                            link = next_sibling.find('a', href=re.compile('/hotel/'))
                
                # Estrategia 3: Buscar en el padre inmediato
                if not link:
                    parent = h3.parent
                    if parent:
                        # Buscar solo en los hijos directos después del h3
                        found_h3 = False
                        for child in parent.children:
                            if child == h3:
                                found_h3 = True
                                continue
                            if found_h3 and hasattr(child, 'name'):
                                if child.name == 'a' and child.get('href', '').startswith('/hotel/'):
                                    link = child
                                    break
                                elif child.name in ['div', 'span']:
                                    # Buscar dentro del hijo
                                    link = child.find('a', href=re.compile('/hotel/'))
                                    if link:
                                        break
                
                # Estrategia 4: Usar find_next para buscar el siguiente <a> en el DOM
                if not link:
                    link = h3.find_next('a', href=re.compile('/hotel/'))
                    # Verificar que el enlace está cerca del h3 (no más de 5 elementos de distancia)
                    if link:
                        # Contar elementos entre h3 y el enlace
                        current = h3
                        distance = 0
                        while current and current != link and distance < 10:
                            current = current.find_next()
                            distance += 1
                        if distance >= 10:
                            link = None  # Demasiado lejos, no es el enlace correcto
                
                if link and link.get('href'):
                    href = link.get('href')
                    if href.startswith('/'):
                        href = f"https://www.booking.com{href}"
                    
                    # Limpiar URL
                    base_url = href.split('?')[0]
                    
                    # Evitar duplicados
                    if base_url not in seen_urls and '/hotel/' in base_url:
                        seen_urls.add(base_url)
                        
                        # Encontrar el contenedor completo del hotel
                        # Buscar el contenedor padre que tenga la clase property-card o similar
                        container = h3
                        for _ in range(20):
                            parent = container.parent
                            if parent:
                                # Verificar si es un contenedor de property card
                                if parent.get('data-testid') == 'property-card-container' or \
                                   parent.get('data-testid') == 'property-card' or \
                                   'property-card' in parent.get('class', []) or \
                                   parent.get('class') and any('a97d60' in c for c in parent.get('class', [])):
                                    container = parent
                                    break
                                # Si tiene precio, probablemente es el contenedor correcto
                                text = parent.get_text()
                                if re.search(r'€\s*\d+|EUR\s*\d+', text) and len(text) > 100:
                                    container = parent
                                    if len(text) > 300:  # Suficiente contenido
                                        break
                            else:
                                break
                        
                        hotel_containers.append({
                            'container': container,
                            'h3': h3,
                            'link': link,
                            'url': base_url
                        })
                        logger.info(f"Hotel encontrado: {h3.get_text(strip=True)} - {base_url}")
            
            logger.info(f"Encontrados {len(hotel_containers)} hoteles únicos por h3->a")
            
            # Si no encontramos hoteles, intentar estrategias alternativas
            if len(hotel_containers) == 0:
                logger.warning("No se encontraron hoteles con h3->a, intentando estrategias alternativas")
                
                # Estrategia alternativa 1: buscar por data-testid
                property_cards = soup.find_all(['div', 'article'], {'data-testid': re.compile('property-card')})
                logger.info(f"Encontradas {len(property_cards)} property cards por data-testid")
                
                for card in property_cards:
                    link = card.find('a', href=re.compile('/hotel/'))
                    if link and link.get('href'):
                        href = link.get('href')
                        if href.startswith('/'):
                            href = f"https://www.booking.com{href}"
                        base_url = href.split('?')[0]
                        
                        if base_url not in seen_urls:
                            seen_urls.add(base_url)
                            h3 = card.find(['h3', 'h2'])
                            hotel_containers.append({
                                'container': card,
                                'h3': h3,
                                'link': link,
                                'url': base_url
                            })
                
                # Estrategia alternativa 2: buscar por clases conocidas
                if len(hotel_containers) == 0:
                    logger.info("Intentando buscar por clases conocidas")
                    class_patterns = ['a97d60', 'd20f4628d0', 'e13098a59f', 'b87c397a13']
                    for pattern in class_patterns:
                        cards = soup.find_all('div', class_=re.compile(pattern))
                        logger.info(f"Encontradas {len(cards)} cards con patrón {pattern}")
                        for card in cards:
                            link = card.find('a', href=re.compile('/hotel/'))
                            if link and link.get('href'):
                                href = link.get('href')
                                if href.startswith('/'):
                                    href = f"https://www.booking.com{href}"
                                base_url = href.split('?')[0]
                                
                                if base_url not in seen_urls:
                                    seen_urls.add(base_url)
                                    h3 = card.find(['h3', 'h2'])
                                    hotel_containers.append({
                                        'container': card,
                                        'h3': h3,
                                        'link': link,
                                        'url': base_url
                                    })
                        if len(hotel_containers) > 0:
                            break
            
            # Procesar los contenedores encontrados
            logger.info(f"Procesando {len(hotel_containers)} contenedores de hoteles")
            
            for i, hotel_info in enumerate(hotel_containers[:max_results]):
                if progress_callback and i % 5 == 0:
                    progress_callback({
                        "message": f"Extrayendo hotel {i+1} de {min(len(hotel_containers), max_results)}",
                        "completed": i,
                        "total": max_results
                    })
                
                # Extraer datos del contenedor
                if isinstance(hotel_info, dict):
                    # Nueva estructura con información pre-extraída
                    hotel_data = self._extract_hotel_from_container_info(hotel_info)
                else:
                    # Estructura antigua (solo contenedor)
                    hotel_data = self._extract_hotel_from_container(hotel_info)
                
                # Añadir el hotel si tiene datos válidos
                if hotel_data and hotel_data.get('url'):
                    hotels.append(hotel_data)
                    logger.info(f"Hotel {len(hotels)}: {hotel_data.get('nombre_hotel', 'Sin nombre')} - {hotel_data.get('url')}")
            
            logger.info(f"Extraídos {len(hotels)} hoteles únicos de {max_results} solicitados")
            
        except Exception as e:
            logger.error(f"Error extrayendo hoteles: {e}")
        
        return hotels
    
    def _extract_hotel_from_container(self, container) -> Dict[str, Any]:
        """Extrae información de un hotel desde su contenedor"""
        hotel_data = {}
        
        try:
            # Nombre del hotel - múltiples estrategias
            name_elem = None
            name_selectors = [
                (['h3', 'div'], {'data-testid': re.compile('title|property-name')}),
                (['h3', 'span'], {'class': re.compile('sr-hotel__name|property-name')}),
                (['a'], {'data-testid': 'title-link'}),
                (['div'], {'class': re.compile('fcab3ed991|a23c043802')})  # Clases específicas de Booking
            ]
            
            for tags, attrs in name_selectors:
                name_elem = container.find(tags, attrs)
                if name_elem:
                    break
            
            # Guardar el nombre del hotel en nombre_hotel en lugar de nombre
            nombre_hotel = ''
            if name_elem:
                nombre_hotel = name_elem.get_text(strip=True)
            
            # URL del hotel - múltiples estrategias
            link_elem = None
            link_selectors = [
                ('a', {'data-testid': re.compile('title-link|property-card-link')}),
                ('a', {'class': re.compile('js-sr-hotel-link|hotel_name_link')}),
                ('a', {'class': re.compile('e13098a59f')}),  # Clase específica de Booking
                ('a', {'href': re.compile('/hotel/')})  # Buscar por patrón de URL
            ]
            
            for tag, attrs in link_selectors:
                link_elem = container.find(tag, attrs)
                if link_elem and link_elem.get('href'):
                    break
            
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    href = f"https://www.booking.com{href}"
                # Limpiar URL - quitar parámetros pero mantener la estructura básica
                base_url = href.split('?')[0]
                if '/hotel/' in base_url:
                    hotel_data['url'] = base_url
            
            # Puntuación
            score_elem = container.find(['div', 'span'], {'data-testid': re.compile('review-score|rating')})
            if not score_elem:
                score_elem = container.find(['div', 'span'], class_=re.compile('review-score|bui-review-score__badge'))
            
            if score_elem:
                score_text = score_elem.get_text(strip=True)
                score_match = re.search(r'(\d+[.,]\d+)', score_text)
                if score_match:
                    hotel_data['puntuacion'] = score_match.group(1).replace(',', '.')
            
            # Número de reseñas
            reviews_elem = container.find(['div', 'span'], {'data-testid': re.compile('review-count|reviews')})
            if not reviews_elem:
                reviews_elem = container.find(['div', 'span'], class_=re.compile('review-score__count|bui-review-score__text'))
            
            if reviews_elem:
                reviews_text = reviews_elem.get_text(strip=True)
                reviews_match = re.search(r'(\d+)', reviews_text)
                if reviews_match:
                    hotel_data['num_resenas'] = int(reviews_match.group(1))
            
            # Precio
            price_elem = container.find(['span', 'div'], {'data-testid': re.compile('price|rate')})
            if not price_elem:
                price_elem = container.find(['span', 'div'], class_=re.compile('prco-inline-block-maker-helper|price'))
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'(\d+)', price_text)
                if price_match:
                    hotel_data['precio'] = price_match.group(1)
            
            # Ubicación
            location_elem = container.find(['span', 'div'], {'data-testid': re.compile('location|address')})
            if not location_elem:
                location_elem = container.find(['span', 'div'], class_=re.compile('sr-hotel__location|address'))
            
            if location_elem:
                hotel_data['ubicacion'] = location_elem.get_text(strip=True)
            
            # Imagen principal
            img_elem = container.find('img', {'data-testid': re.compile('image|photo')})
            if not img_elem:
                img_elem = container.find('img', class_=re.compile('hotel_image|property-image'))
            
            if img_elem and img_elem.get('src'):
                hotel_data['imagen_principal'] = img_elem.get('src')
            
            # Guardar el nombre del hotel en lugar de tipo_propiedad
            if nombre_hotel:
                hotel_data['nombre_hotel'] = nombre_hotel
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del hotel: {e}")
        
        return hotel_data
    
    def _extract_hotel_from_container_info(self, hotel_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae información de un hotel desde la estructura con información pre-extraída"""
        hotel_data = {}
        
        try:
            # URL ya la tenemos
            hotel_data['url'] = hotel_info.get('url', '')
            
            # Nombre del hotel desde el h3 - ahora se guarda en nombre_hotel
            nombre_hotel = ''
            if hotel_info.get('h3'):
                # Obtener solo el texto del h3, excluyendo elementos hijos
                h3_elem = hotel_info['h3']
                # Buscar el texto directo o el primer enlace con el nombre
                nombre_link = h3_elem.find('a')
                if nombre_link:
                    nombre_hotel = nombre_link.get_text(strip=True)
                else:
                    # Si no hay enlace, obtener el texto directo
                    nombre_hotel = h3_elem.get_text(strip=True)
                
                # Limpiar el texto de "Se abre en una nueva ventana" y similares
                nombre_hotel = nombre_hotel.replace("Se abre en una nueva ventana", "").strip()
            
            container = hotel_info.get('container')
            if container:
                # Puntuación
                score_elem = container.find(['div', 'span'], {'data-testid': re.compile('review-score|rating')})
                if not score_elem:
                    score_elem = container.find(['div', 'span'], class_=re.compile('review-score|bui-review-score__badge|d10a6220b4'))
                
                if score_elem:
                    score_text = score_elem.get_text(strip=True)
                    score_match = re.search(r'(\d+[.,]\d+)', score_text)
                    if score_match:
                        hotel_data['puntuacion'] = score_match.group(1).replace(',', '.')
                
                # Número de reseñas
                reviews_elem = container.find(['div', 'span'], text=re.compile(r'\d+\s*(opiniones|reviews|comentarios)', re.I))
                if reviews_elem:
                    reviews_text = reviews_elem.get_text(strip=True)
                    reviews_match = re.search(r'(\d+)', reviews_text)
                    if reviews_match:
                        hotel_data['num_resenas'] = int(reviews_match.group(1))
                
                # Precio - buscar más agresivamente
                price_text = container.get_text()
                price_match = re.search(r'€\s*(\d+)', price_text)
                if price_match:
                    hotel_data['precio'] = price_match.group(1)
                
                # Ubicación
                location_elem = container.find(['span', 'div'], {'data-testid': re.compile('location|address')})
                if not location_elem:
                    # Buscar por patrones de texto comunes para ubicación
                    location_elem = container.find(text=re.compile(r'Mostrar en el mapa|Ver en mapa|Show on map', re.I))
                    if location_elem:
                        location_elem = location_elem.find_parent(['span', 'div'])
                
                if location_elem:
                    # Obtener el texto del elemento padre si es necesario
                    location_text = location_elem.get_text(strip=True)
                    # Limpiar el texto de ubicación
                    location_text = re.sub(r'Mostrar en el mapa|Ver en mapa|Show on map', '', location_text, flags=re.I).strip()
                    if location_text:
                        hotel_data['ubicacion'] = location_text
                
                # Imagen principal
                img_elem = container.find('img')
                if img_elem and img_elem.get('src'):
                    src = img_elem.get('src')
                    # Asegurarse de que es una imagen de hotel
                    if 'bstatic.com' in src or src.startswith('//'):
                        if src.startswith('//'):
                            src = 'https:' + src
                        hotel_data['imagen_principal'] = src
                
                # Guardar el nombre del hotel en lugar de tipo_propiedad
                if nombre_hotel:
                    hotel_data['nombre_hotel'] = nombre_hotel
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del hotel desde info: {e}")
        
        return hotel_data
