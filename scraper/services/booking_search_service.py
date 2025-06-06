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
            # Buscar contenedores de hoteles con múltiples estrategias
            all_containers = []
            
            # Estrategia 1: data-testid más específicos
            selectors = [
                ('div', {'data-testid': 'property-card'}),
                ('div', {'data-testid': 'property-card-container'}),
                ('article', {'data-testid': 'property-card'}),
                ('div', {'data-testid': re.compile('item|card')}),
            ]
            
            for tag, attrs in selectors:
                containers = soup.find_all(tag, attrs)
                all_containers.extend(containers)
            
            # Estrategia 2: clases específicas de Booking
            class_patterns = [
                'sr_property_block',
                'sr_item',
                'd20f4628d0',  # Clase específica de contenedor
                'a826ba81c4',  # Otra clase común
                'fe87d598e8',  # Clase de lista de propiedades
                'bcbf33c5c3',  # Contenedor de propiedad
                'c82435a4b8',  # Otra clase de contenedor
                'a1b3f50dcd',  # Clase de resultado de búsqueda
                'f9a06b8a5b',  # Contenedor de propiedad alternativo
            ]
            
            for pattern in class_patterns:
                containers = soup.find_all('div', class_=re.compile(pattern))
                all_containers.extend(containers)
            
            # Estrategia 3: buscar por estructura - mejorada
            # Buscar todos los enlaces a hoteles y sus contenedores
            hotel_links = soup.find_all('a', href=re.compile('/hotel/'))
            for link in hotel_links:
                # Buscar el contenedor padre que englobe toda la información del hotel
                parent = link
                for _ in range(10):  # Subir hasta 10 niveles
                    parent = parent.find_parent(['div', 'article'])
                    if parent:
                        # Verificar si este contenedor tiene información de hotel
                        text_content = parent.get_text()
                        if any(indicator in text_content.lower() for indicator in ['€', 'eur', 'precio', 'habitación', 'camas']):
                            if parent not in all_containers:
                                all_containers.append(parent)
                            break
            
            # Estrategia 4: buscar por atributos específicos
            # Buscar elementos con data-hotelid o similares
            for attr in ['data-hotelid', 'data-hotel-id', 'data-id']:
                elements = soup.find_all(attrs={attr: True})
                all_containers.extend(elements)
            
            # Estrategia 5: buscar contenedores que tengan botón "Ver disponibilidad"
            availability_buttons = soup.find_all(text=re.compile('Ver disponibilidad|Book now|Reservar', re.I))
            for button in availability_buttons:
                parent = button
                for _ in range(8):
                    parent = parent.find_parent(['div', 'article'])
                    if parent and parent not in all_containers:
                        # Verificar que es un contenedor de hotel
                        if parent.find('a', href=re.compile('/hotel/')):
                            all_containers.append(parent)
                            break
            
            # Estrategia 6: Buscar por el patrón específico de las cards de Booking
            # Buscar todos los elementos que tengan tanto un enlace como un precio
            price_elements = soup.find_all(text=re.compile('€|EUR'))
            for price in price_elements:
                parent = price
                for _ in range(10):
                    parent = parent.find_parent(['div', 'article'])
                    if parent:
                        # Verificar si tiene un enlace a hotel
                        hotel_link = parent.find('a', href=re.compile('/hotel/'))
                        if hotel_link and parent not in all_containers:
                            all_containers.append(parent)
                            break
            
            # Log de depuración
            logger.info(f"Total de contenedores encontrados (antes de filtrar): {len(all_containers)}")
            
            # Eliminar duplicados manteniendo el orden
            hotel_containers = []
            seen_containers = set()
            seen_hotel_names = set()
            
            for container in all_containers:
                # Obtener el texto del contenedor para verificar duplicados
                container_text = container.get_text()
                
                # Buscar el nombre del hotel en el contenedor
                hotel_name = None
                name_elem = container.find(['h3', 'h2', 'a'], text=True)
                if name_elem:
                    hotel_name = name_elem.get_text(strip=True)
                
                # Usar una combinación de factores para identificar duplicados
                container_id = f"{hotel_name}_{len(container_text)}"
                
                if container_id not in seen_containers and (not hotel_name or hotel_name not in seen_hotel_names):
                    # Verificar que realmente es un contenedor de hotel válido
                    has_link = container.find('a', href=re.compile('/hotel/'))
                    has_price = any(symbol in container_text for symbol in ['€', 'EUR', '$'])
                    
                    if has_link or has_price:
                        seen_containers.add(container_id)
                        if hotel_name:
                            seen_hotel_names.add(hotel_name)
                        hotel_containers.append(container)
            
            # Ordenar por tamaño del contenedor (los más grandes primero, probablemente más completos)
            hotel_containers.sort(key=lambda x: len(str(x)), reverse=True)
            
            # Eliminar contenedores que estén contenidos dentro de otros
            final_containers = []
            for i, container in enumerate(hotel_containers):
                is_child = False
                for j, other in enumerate(hotel_containers):
                    if i != j and container in other.descendants:
                        is_child = True
                        break
                if not is_child:
                    final_containers.append(container)
            
            hotel_containers = final_containers
            
            # Si tenemos muy pocos contenedores, intentar una estrategia más agresiva
            if len(hotel_containers) < max_results:
                logger.info(f"Solo {len(hotel_containers)} contenedores encontrados, buscando más agresivamente...")
                
                # Buscar cualquier div que contenga un enlace de hotel y un precio
                additional_containers = []
                all_divs = soup.find_all('div')
                for div in all_divs:
                    if div not in hotel_containers:
                        has_hotel_link = div.find('a', href=re.compile('/hotel/'))
                        has_price = re.search(r'€\s*\d+|EUR\s*\d+', div.get_text())
                        if has_hotel_link and has_price:
                            # Verificar que no sea demasiado pequeño
                            if len(div.get_text()) > 100:
                                additional_containers.append(div)
                
                # Filtrar para evitar contenedores anidados
                for container in additional_containers:
                    is_nested = False
                    for existing in hotel_containers:
                        if container in existing.descendants or existing in container.descendants:
                            is_nested = True
                            break
                    if not is_nested:
                        hotel_containers.append(container)
            
            logger.info(f"Encontrados {len(hotel_containers)} contenedores únicos de hoteles")
            
            for i, container in enumerate(hotel_containers):
                if len(hotels) >= max_results:
                    break
                    
                if progress_callback and i % 5 == 0:
                    progress_callback({
                        "message": f"Extrayendo hotel {len(hotels)+1} de {max_results}",
                        "completed": len(hotels),
                        "total": max_results
                    })
                
                hotel_data = self._extract_hotel_from_container(container)
                
                # Verificar que tenemos datos válidos y no duplicados
                if hotel_data and hotel_data.get('url'):
                    hotel_url = hotel_data['url']
                    if hotel_url not in seen_urls:
                        seen_urls.add(hotel_url)
                        hotels.append(hotel_data)
                        logger.info(f"Hotel {len(hotels)}: {hotel_data.get('nombre', 'Sin nombre')}")
            
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
            
            if name_elem:
                hotel_data['nombre'] = name_elem.get_text(strip=True)
            
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
            
            # Tipo de propiedad
            property_type_elem = container.find(['span', 'div'], class_=re.compile('property-type|accommodation-type'))
            if property_type_elem:
                hotel_data['tipo_propiedad'] = property_type_elem.get_text(strip=True)
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del hotel: {e}")
        
        return hotel_data
