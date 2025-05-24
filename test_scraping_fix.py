"""
Script de prueba para verificar que el scraping funciona correctamente
después de los cambios en httpx_service.py
"""
import asyncio
from services.scraping_service import TagScrapingService
from services.utils.httpx_service import HttpxService, create_fast_httpx_config
import json

def test_single_url():
    """Prueba el scraping de una sola URL"""
    print("=== Prueba de URL individual ===")
    
    # Crear servicio
    httpx_service = HttpxService(create_fast_httpx_config())
    
    # URL de prueba
    test_url = "https://destinia.com/guides/10-mejores-hoteles-en-granada-por-calidad-y-precio/"
    
    # Obtener HTML
    result, html = httpx_service.get_html_sync(test_url)
    
    print(f"URL: {test_url}")
    print(f"Resultado: {json.dumps(result, indent=2)}")
    print(f"Longitud HTML: {len(html)} caracteres")
    
    if html:
        # Analizar contenido
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar título
        title = soup.find('title')
        print(f"Título: {title.text.strip() if title else 'No encontrado'}")
        
        # Buscar headers
        for level in ['h1', 'h2', 'h3']:
            headers = soup.find_all(level)
            print(f"\n{level.upper()} encontrados: {len(headers)}")
            for i, header in enumerate(headers[:3]):  # Mostrar solo los primeros 3
                print(f"  {i+1}. {header.text.strip()}")
            if len(headers) > 3:
                print(f"  ... y {len(headers) - 3} más")
    
    print("\n" + "="*50 + "\n")

def test_tag_scraping_service():
    """Prueba el servicio completo de scraping de tags"""
    print("=== Prueba del TagScrapingService ===")
    
    # URLs de prueba
    test_urls = [
        "https://destinia.com/guides/10-mejores-hoteles-en-granada-por-calidad-y-precio/",
        "https://www.booking.com/city/es/granada.es.html",
        "https://es.luxuryhotel.world/granada-spain/",
        "https://www.ideal.es/granada/mejores-hoteles-granada-segun-the-times-20230510141806-nt.html",
        "https://www.tripadvisor.es/Hotels-g187441-zff12-Granada_Province_of_Granada_Andalucia-Hotels.html"
    ]
    
    # Crear servicio
    tag_service = TagScrapingService()
    
    # Procesar URLs
    results = tag_service.scrape_tags_from_urls(test_urls[:3], extract_content=False)
    
    # Mostrar resultados
    for i, result in enumerate(results):
        print(f"\n--- Resultado {i+1} ---")
        print(f"URL: {result.get('url')}")
        print(f"Status: {result.get('status_code')}")
        print(f"Método: {result.get('method', 'N/A')}")
        
        if result.get('error'):
            print(f"Error: {result.get('error')}")
            print(f"Necesita Playwright: {result.get('needs_playwright', False)}")
        else:
            print(f"Título: {result.get('title', 'No encontrado')}")
            print(f"Descripción: {result.get('description', 'No encontrada')[:100]}...")
            
            h1_data = result.get('h1', {})
            if h1_data:
                if 'headers' in h1_data:
                    # Caso donde no hay estructura H1 pero sí otros headers
                    print(f"Headers encontrados: {len(h1_data['headers'])}")
                    for header in h1_data['headers'][:5]:
                        print(f"  - {header['level']}: {header['text']}")
                else:
                    # Caso con estructura H1 normal
                    print(f"H1: {h1_data.get('titulo', 'No encontrado')}")
                    h2_count = len(h1_data.get('h2', []))
                    print(f"H2 encontrados: {h2_count}")
                    for h2 in h1_data.get('h2', [])[:3]:
                        print(f"  - H2: {h2.get('titulo')}")
                        h3_count = len(h2.get('h3', []))
                        if h3_count > 0:
                            print(f"    H3 encontrados: {h3_count}")
    
    print("\n" + "="*50 + "\n")

def test_httpx_check_if_blocked():
    """Prueba específica de la función _check_if_blocked"""
    print("=== Prueba de _check_if_blocked ===")
    
    httpx_service = HttpxService()
    
    # Casos de prueba
    test_cases = [
        # (html, status_code, expected_needs_playwright, description)
        ("<html><body><h1>Test</h1><p>Content</p></body></html>", 200, False, "HTML válido con headers"),
        ("<html><body><p>Solo párrafos</p></body></html>", 200, False, "HTML válido sin headers"),
        ("<html><body>Contenido mínimo</body></html>", 200, False, "HTML mínimo pero status 200"),
        ("", 200, False, "HTML vacío pero status 200"),
        ("<html><body>cloudflare ray id: 123</body></html>", 200, True, "Cloudflare detectado"),
        ("<html><body>Please enable JavaScript</body></html>", 200, True, "JavaScript requerido"),
        ("Error", 403, True, "Status 403"),
        ("Error", 404, True, "Status 404"),
        ("Redirecting...", 301, False, "Status 301 redirección"),
    ]
    
    for html, status, expected, desc in test_cases:
        needs_playwright, reason = httpx_service._check_if_blocked(html, status)
        result = "✅" if needs_playwright == expected else "❌"
        print(f"{result} {desc}: needs_playwright={needs_playwright}, reason='{reason}'")
    
    print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    try:
        # Ejecutar pruebas
        print("Iniciando pruebas de scraping...\n")
        
        # Prueba 1: Verificar la función _check_if_blocked
        test_httpx_check_if_blocked()
        
        # Prueba 2: URL individual
        test_single_url()
        
        # Prueba 3: Servicio completo
        test_tag_scraping_service()
        
        print("Pruebas completadas!")
    except Exception as e:
        print(f"Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
