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
                    close_button = await page.query_selector('[aria-label="Cerrar"]')
                    if close_button:
                        await close_button.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass
                
                # Obtener el HTML
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                # Extraer hoteles
                hotels = await self._extract_hotels_from_search(page, soup, max_results, progress_callback)
                
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
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Extrae información de hoteles de los resultados de búsqueda"""
        hotels = []
        
        try:
            # Buscar contenedores de hoteles (Booking cambia las clases frecuentemente)
            hotel_containers = soup.find_all('div', {'data-testid': re.compile('property-card|hotel-card')})
            
            if not hotel_containers:
                # Intentar con otras clases comunes
                hotel_containers = soup.find_all('div', class_=re.compile('sr_property_block|sr_item|property-card'))
            
            logger.info(f"Encontrados {len(hotel_containers)} contenedores de hoteles")
            
            for i, container in enumerate(hotel_containers[:max_results]):
                if progress_callback and i % 5 == 0:
                    progress_callback({
                        "message": f"Extrayendo hotel {i+1} de {min(len(hotel_containers), max_results)}",
                        "completed": i,
                        "total": max_results
                    })
                
                hotel_data = self._extract_hotel_from_container(container)
                if hotel_data and hotel_data.get('url'):
                    hotels.append(hotel_data)
                
                if len(hotels) >= max_results:
                    break
            
        except Exception as e:
            logger.error(f"Error extrayendo hoteles: {e}")
        
        return hotels
    
    def _extract_hotel_from_container(self, container) -> Dict[str, Any]:
        """Extrae información de un hotel desde su contenedor"""
        hotel_data = {}
        
        try:
            # Nombre del hotel
            name_elem = container.find(['h3', 'div'], {'data-testid': re.compile('title|property-name')})
            if not name_elem:
                name_elem = container.find(['h3', 'span'], class_=re.compile('sr-hotel__name|property-name'))
            
            if name_elem:
                hotel_data['nombre'] = name_elem.get_text(strip=True)
            
            # URL del hotel
            link_elem = container.find('a', {'data-testid': re.compile('title-link|property-card-link')})
            if not link_elem:
                link_elem = container.find('a', class_=re.compile('js-sr-hotel-link|hotel_name_link'))
            
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    href = f"https://www.booking.com{href}"
                hotel_data['url'] = href.split('?')[0]  # Quitar parámetros de búsqueda
            
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
