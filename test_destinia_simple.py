"""
Script simplificado para debuggear Destinia
"""
import httpx
from bs4 import BeautifulSoup

def test_destinia():
    url = "https://destinia.com/guides/10-mejores-hoteles-en-granada-por-calidad-y-precio/"
    
    # Headers para parecer un navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    }
    
    try:
        # Obtener HTML
        response = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
        html = response.text
        
        print(f"URL: {url}")
        print(f"Status Code: {response.status_code}")
        print(f"HTML Length: {len(html)}")
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Verificar headers
            h1_tags = soup.find_all('h1')
            h2_tags = soup.find_all('h2')
            h3_tags = soup.find_all('h3')
            
            print(f"\nHeaders encontrados:")
            print(f"H1: {len(h1_tags)}")
            if h1_tags:
                for i, h1 in enumerate(h1_tags[:3]):
                    print(f"  H1[{i}]: {h1.text.strip()[:50]}...")
            
            print(f"H2: {len(h2_tags)}")
            if h2_tags:
                for i, h2 in enumerate(h2_tags[:3]):
                    print(f"  H2[{i}]: {h2.text.strip()[:50]}...")
                    
            print(f"H3: {len(h3_tags)}")
            
            # Verificar scripts
            scripts = soup.find_all('script')
            print(f"\nScripts encontrados: {len(scripts)}")
            
            # Verificar indicadores de JavaScript
            lower_html = html.lower()
            js_indicators = [
                'react', 'vue', 'angular', 'next.js',
                'webpack', 'bundle.js', 'app.js',
                'lazyload', 'data-src'
            ]
            
            found_indicators = []
            for indicator in js_indicators:
                if indicator in lower_html:
                    found_indicators.append(indicator)
            
            print(f"\nIndicadores JS encontrados: {found_indicators}")
            
            # Verificar título
            title = soup.find('title')
            if title:
                print(f"\nTítulo: {title.text.strip()}")
            
            # Mostrar primeros 2000 caracteres del body
            body = soup.find('body')
            if body:
                body_text = body.get_text(strip=True)
                print(f"\nPrimeros 500 caracteres del body text:")
                print(body_text[:500])
            
            # Buscar cualquier contenido que parezca un header
            print(f"\nBuscando otros posibles headers...")
            # Buscar divs o spans con clases que sugieran headers
            possible_headers = soup.find_all(['div', 'span'], class_=lambda x: x and any(word in str(x).lower() for word in ['title', 'heading', 'header']))
            print(f"Posibles headers encontrados: {len(possible_headers)}")
            for i, header in enumerate(possible_headers[:3]):
                if header.text.strip():
                    print(f"  [{i}]: {header.text.strip()[:50]}...")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_destinia()
