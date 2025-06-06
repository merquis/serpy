"""
Servicio de Booking Scraping - Extracción de datos de hoteles
"""
import json
import datetime
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import logging
import asyncio
from rebrowser_playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class BookingScrapingService:
    """Servicio para extraer datos de hoteles de Booking.com"""
    
    def __init__(self):
        pass
    
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
                            progress_info = {
                                "message": f"Procesando {i+1}/{len(urls)}: {url}",
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
                        
                        # Obtener el HTML
                        html = await page.content()
                        
                        # Cerrar la página
                        await page.close()
                        
                        # Parsear el HTML
                        soup = BeautifulSoup(html, "html.parser")
                        hotel_data = self._parse_hotel_html(soup, url)
                        hotel_data["method"] = "rebrowser-playwright"
                        results.append(hotel_data)
                        
                    except Exception as e:
                        logger.error(f"Error procesando {url}: {e}")
                        results.append({
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
    
    
    def _parse_hotel_html(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Parsea el HTML de la página del hotel"""
        # Extraer parámetros de la URL
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # Parámetros de búsqueda
        group_adults = query_params.get('group_adults', [''])[0]
        group_children = query_params.get('group_children', [''])[0]
        no_rooms = query_params.get('no_rooms', [''])[0]
        checkin = query_params.get('checkin', [''])[0]
        checkout = query_params.get('checkout', [''])[0]
        dest_type = query_params.get('dest_type', [''])[0]
        
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
        
        return {
            "url_original": url,
            "fecha_scraping": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "busqueda_checkin": checkin,
            "busqueda_checkout": checkout,
            "busqueda_adultos": group_adults,
            "busqueda_ninos": group_children,
            "busqueda_habitaciones": no_rooms,
            "busqueda_tipo_destino": dest_type,
            "nombre_alojamiento": data_extraida.get("name", titulo_h1) if data_extraida else titulo_h1,
            "tipo_alojamiento": data_extraida.get("@type", "Hotel") if data_extraida else "Hotel",
            "direccion": address_info.get("streetAddress"),
            "codigo_postal": address_info.get("postalCode"),
            "ciudad": address_info.get("addressLocality"),
            "pais": address_info.get("addressCountry"),
            "url_hotel_booking": data_extraida.get("url") if data_extraida else url,
            "descripcion_corta": data_extraida.get("description") if data_extraida else "",
            "valoracion_global": rating_info.get("ratingValue"),
            "mejor_valoracion_posible": rating_info.get("bestRating", "10"),
            "numero_opiniones": rating_info.get("reviewCount"),
            "rango_precios": data_extraida.get("priceRange") if data_extraida else "",
            "titulo_h1": titulo_h1,
            "subtitulos_h2": h2s,
            "servicios_principales": servicios,
            "imagenes": imagenes,
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
