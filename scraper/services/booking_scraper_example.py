"""
Ejemplo de uso del servicio BookingExtraerDatosService de forma modular
"""
import asyncio
import json
from typing import List, Dict, Any
from booking_extraer_datos_service import BookingExtraerDatosService

async def scrape_hotels_from_json(json_data: str) -> List[Dict[str, Any]]:
    """
    Ejemplo de función que usa el servicio para scrapear hoteles desde un JSON
    
    Args:
        json_data: JSON string con resultados de búsqueda
        
    Returns:
        Lista de hoteles con datos extraídos
    """
    # Crear instancia del servicio
    service = BookingExtraerDatosService()
    
    # Extraer URLs del JSON
    urls = service.extract_urls_from_json(json_data)
    
    if not urls:
        print("No se encontraron URLs en el JSON")
        return []
    
    print(f"Se encontraron {len(urls)} URLs para scrapear")
    
    # Función de callback para mostrar progreso
    def progress_callback(info: Dict[str, Any]):
        print(f"[{info['completed']}/{info['total']}] {info['message']}")
    
    # Ejecutar scraping
    results = await service.scrape_hotels(urls, progress_callback=progress_callback)
    
    return results

async def scrape_hotels_from_mixed_input(input_text: str) -> List[Dict[str, Any]]:
    """
    Ejemplo que acepta entrada mixta (URLs, JSON, etc.)
    
    Args:
        input_text: Texto con URLs, JSON o mezcla
        
    Returns:
        Lista de hoteles con datos extraídos
    """
    service = BookingExtraerDatosService()
    
    # Parsear URLs de cualquier formato
    urls = service.parse_urls_input(input_text)
    
    if not urls:
        print("No se encontraron URLs válidas")
        return []
    
    print(f"URLs encontradas: {len(urls)}")
    for i, url in enumerate(urls[:3]):  # Mostrar primeras 3
        print(f"  {i+1}. {url}")
    
    # Ejecutar scraping
    results = await service.scrape_hotels(urls)
    
    return results

def main():
    """Ejemplo de uso"""
    
    # Ejemplo 1: JSON de búsqueda
    json_ejemplo = """{
        "search_url": "https://www.booking.com/searchresults.es.html",
        "hotels": [
            {
                "url": "https://www.booking.com/hotel/es/nivaria-beach.es.html",
                "nombre_hotel": "Kora Nivaria Beach",
                "url_arg": "https://www.booking.com/hotel/es/nivaria-beach.es.html?checkin=2025-06-09&checkout=2025-06-10&group_adults=2&no_rooms=1"
            },
            {
                "url": "https://www.booking.com/hotel/es/jardin-tropical.es.html",
                "nombre_hotel": "Dreams Jardin Tropical Resort & Spa",
                "url_arg": "https://www.booking.com/hotel/es/jardin-tropical.es.html?checkin=2025-06-09&checkout=2025-06-10&group_adults=2&no_rooms=1"
            }
        ]
    }"""
    
    # Ejemplo 2: URLs separadas por comas
    urls_comas = """
    https://www.booking.com/hotel/es/nivaria-beach.es.html?checkin=2025-06-09&checkout=2025-06-10,
    https://www.booking.com/hotel/es/jardin-tropical.es.html?checkin=2025-06-09&checkout=2025-06-10
    """
    
    # Ejemplo 3: URLs separadas por líneas
    urls_lineas = """
    https://www.booking.com/hotel/es/nivaria-beach.es.html?checkin=2025-06-09&checkout=2025-06-10&group_adults=2&no_rooms=1
    https://www.booking.com/hotel/es/jardin-tropical.es.html?checkin=2025-06-09&checkout=2025-06-10&group_adults=2&no_rooms=1
    """
    
    # Ejecutar ejemplo con JSON
    print("=== Ejemplo 1: Scraping desde JSON ===")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        results = loop.run_until_complete(scrape_hotels_from_json(json_ejemplo))
        
        print(f"\nResultados obtenidos: {len(results)}")
        for hotel in results:
            if not hotel.get("error"):
                print(f"✓ {hotel.get('nombre_alojamiento', 'Sin nombre')}")
                print(f"  - Valoración: {hotel.get('valoracion_global', 'N/A')}/10")
                print(f"  - Ciudad: {hotel.get('ciudad', 'N/A')}")
                print(f"  - Imágenes: {len(hotel.get('imagenes', []))}")
            else:
                print(f"✗ Error: {hotel.get('error')}")
    
    finally:
        loop.close()

if __name__ == "__main__":
    main()
