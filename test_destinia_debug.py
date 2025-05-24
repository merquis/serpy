"""
Script para debuggear por qué Destinia no está siendo detectada como necesitando Playwright
"""
import asyncio
from services.utils.httpx_service import HttpxService, create_stealth_httpx_config
from bs4 import BeautifulSoup

async def test_destinia():
    url = "https://destinia.com/guides/10-mejores-hoteles-en-granada-por-calidad-y-precio/"
    
    # Crear servicio httpx
    config = create_stealth_httpx_config()
    service = HttpxService(config)
    
    # Obtener HTML
    result, html = await service.get_html(url)
    
    print(f"URL: {url}")
    print(f"Status Code: {result.get('status_code')}")
    print(f"Method: {result.get('method')}")
    print(f"Needs Playwright: {result.get('needs_playwright')}")
    print(f"Error: {result.get('error')}")
    print(f"HTML Length: {len(html)}")
    
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Verificar headers
        h1_count = len(soup.find_all('h1'))
        h2_count = len(soup.find_all('h2'))
        h3_count = len(soup.find_all('h3'))
        
        print(f"\nHeaders encontrados:")
        print(f"H1: {h1_count}")
        print(f"H2: {h2_count}")
        print(f"H3: {h3_count}")
        
        # Verificar scripts
        scripts = soup.find_all('script')
        print(f"\nScripts encontrados: {len(scripts)}")
        
        # Verificar indicadores de JavaScript
        lower_html = html.lower()
        js_indicators = [
            'react-root', '__next', 'vue-app', 'ng-app', 'angular',
            'loading', 'spinner', 'skeleton',
            'webpack', 'bundle.js', 'app.js', 'main.js',
            '<div id="root"></div>', '<div id="app"></div>',
            'data-react', 'data-vue', 'data-ng',
            'lazy-load', 'lazyload', 'data-src'
        ]
        
        found_indicators = []
        for indicator in js_indicators:
            if indicator in lower_html:
                found_indicators.append(indicator)
        
        print(f"\nIndicadores JS encontrados: {found_indicators}")
        
        # Verificar noscript
        noscript = soup.find('noscript')
        print(f"\nTiene noscript: {bool(noscript)}")
        
        # Verificar contenido significativo
        body = soup.find('body')
        if body:
            significant_tags = body.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article', 'section', 'main'])
            print(f"\nTags significativos en body: {len(significant_tags)}")
        
        # Mostrar primeros 1000 caracteres del HTML
        print(f"\nPrimeros 1000 caracteres del HTML:")
        print(html[:1000])
        
        # Verificar si debería haber usado Playwright según nuestra lógica
        has_headers = h1_count > 0 or h2_count > 0 or h3_count > 0
        has_js_indicators = len(found_indicators) > 0
        has_many_scripts = len(scripts) > 10
        
        print(f"\n¿Debería usar Playwright?")
        print(f"- No hay headers y hay indicadores JS: {not has_headers and has_js_indicators}")
        print(f"- No hay headers y muchos scripts: {not has_headers and has_many_scripts}")

if __name__ == "__main__":
    asyncio.run(test_destinia())
