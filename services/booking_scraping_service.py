"""
Servicio de Booking Scraping - Extracción de datos de hoteles
"""
import asyncio
import json
import datetime
import re
from typing import List, Dict, Any, Optional, Tuple
from playwright.async_api import async_playwright, Browser
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

class BookingScrapingService:
    """Servicio para extraer datos de hoteles de Booking.com"""
    
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
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            
            try:
                # Procesar todas las URLs en paralelo
                tasks = []
                for i, url in enumerate(urls):
                    if progress_callback:
                        progress_callback(f"Procesando {i+1}/{len(urls)}: {url}")
                    tasks.append(self._scrape_single_hotel(url, browser))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar resultados
                final_results = []
                for i, res in enumerate(results):
                    url = urls[i]
                    if isinstance(res, Exception):
                        final_results.append({
                            "error": "Fallo_Excepcion_Gather",
                            "url_original": url,
                            "details": str(res)
                        })
                    elif isinstance(res, dict):
                        final_results.append(res)
                    else:
                        final_results.append({
                            "error": "Fallo_ResultadoInesperado",
                            "url_original": url,
                            "details": str(res)
                        })
                
                return final_results
                
            finally:
                await browser.close()
    
    async def _scrape_single_hotel(
        self,
        url: str,
        browser: Browser
    ) -> Dict[str, Any]:
        """Extrae datos de un solo hotel"""
        context = None
        page = None
        
        try:
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            
            # Configurar headers
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            })
            
            # Navegar a la URL
            await page.goto(url, timeout=60000, wait_until="networkidle")
            await page.wait_for_selector("#hp_hotel_name, h1", timeout=15000)
            
            # Obtener HTML
            html = await page.content()
            if not html:
                return {
                    "error": "Fallo_HTML_Vacio",
                    "url_original": url,
                    "details": "No se obtuvo contenido HTML"
                }
            
            # Parsear HTML
            soup = BeautifulSoup(html, "html.parser")
            result = self._parse_hotel_html(soup, url)
            
            return result
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                "error": f"Fallo_Excepcion_{type(e).__name__}",
                "url_original": url,
                "details": str(e)
            }
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
            if context:
                try:
                    await context.close()
                except:
                    pass
    
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