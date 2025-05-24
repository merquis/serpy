"""
Script de prueba para verificar el funcionamiento del servicio httpx
"""
import asyncio
from services.utils.httpx_service import HttpxService, create_fast_httpx_config, create_stealth_httpx_config, httpx_requests

async def test_async_httpx():
    """Prueba el servicio httpx asíncrono"""
    print("=== Prueba Asíncrona ===")
    
    # Crear servicio con configuración rápida
    service = HttpxService(create_fast_httpx_config())
    
    # URLs de prueba
    test_urls = [
        "https://httpbin.org/status/200",  # Debería funcionar con httpx
        "https://httpbin.org/status/403",  # Debería detectar que necesita Playwright
        "https://example.com",             # Sitio simple que debería funcionar
    ]
    
    for url in test_urls:
        print(f"\nProbando: {url}")
        result, html = await service.get_html(url)
        
        print(f"  Método: {result.get('method', 'N/A')}")
        print(f"  Status: {result.get('status_code', 'N/A')}")
        print(f"  Éxito: {result.get('success', False)}")
        print(f"  Necesita Playwright: {result.get('needs_playwright', False)}")
        if html:
            print(f"  HTML recibido: {len(html)} caracteres")
        if result.get('error'):
            print(f"  Error: {result.get('error')}")

def test_sync_httpx():
    """Prueba el servicio httpx síncrono (reemplazo de requests)"""
    print("\n\n=== Prueba Síncrona (Reemplazo de requests) ===")
    
    # Usar la instancia global httpx_requests
    test_urls = [
        "https://httpbin.org/status/200",
        "https://example.com",
    ]
    
    for url in test_urls:
        print(f"\nProbando con httpx_requests.get(): {url}")
        try:
            response = httpx_requests.get(url, timeout=10)
            print(f"  Status Code: {response.status_code}")
            print(f"  OK: {response.ok}")
            print(f"  URL: {response.url}")
            if response.text:
                print(f"  Contenido: {len(response.text)} caracteres")
        except Exception as e:
            print(f"  Error: {e}")

def test_headers_extraction():
    """Prueba la extracción de headers"""
    print("\n\n=== Prueba de Extracción de Headers ===")
    
    service = HttpxService()
    
    # HTML de ejemplo
    test_html = """
    <html>
    <head><title>Página de Prueba</title></head>
    <body>
        <h1>Título Principal</h1>
        <p>Contenido del h1</p>
        <h2>Subtítulo 1</h2>
        <p>Contenido del h2</p>
        <h3>Sub-subtítulo 1.1</h3>
        <h2>Subtítulo 2</h2>
        <h3>Sub-subtítulo 2.1</h3>
        <h3>Sub-subtítulo 2.2</h3>
    </body>
    </html>
    """
    
    headers = service.extract_headers(test_html, ['h1', 'h2', 'h3'])
    
    print("Headers extraídos:")
    for level, texts in headers.items():
        print(f"  {level}: {texts}")

def test_cloudscraper():
    """Prueba la funcionalidad de cloudscraper"""
    print("\n\n=== Prueba de Cloudscraper ===")
    
    # Crear servicio con configuración stealth (incluye cloudscraper)
    service = HttpxService(create_stealth_httpx_config())
    
    # Esta URL podría tener protección Cloudflare
    url = "https://httpbin.org/headers"
    
    print(f"Probando con cloudscraper habilitado: {url}")
    result, html = service.get_html_sync(url)
    
    print(f"  Método usado: {result.get('method', 'N/A')}")
    print(f"  Éxito: {result.get('success', False)}")
    if html:
        print(f"  HTML recibido: {len(html)} caracteres")

if __name__ == "__main__":
    print("Iniciando pruebas del servicio httpx...\n")
    
    # Pruebas síncronas
    test_sync_httpx()
    test_headers_extraction()
    test_cloudscraper()
    
    # Pruebas asíncronas
    print("\n" + "="*50)
    asyncio.run(test_async_httpx())
    
    print("\n\nPruebas completadas!")
