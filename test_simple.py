"""
Script simple para probar una sola URL y ver qué está pasando
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.utils.httpx_service import HttpxService, create_fast_httpx_config
from bs4 import BeautifulSoup

def test_one_url():
    # URL de prueba
    url = "https://destinia.com/guides/10-mejores-hoteles-en-granada-por-calidad-y-precio/"
    
    print(f"Probando URL: {url}")
    print("-" * 80)
    
    # Crear servicio httpx
    httpx_service = HttpxService(create_fast_httpx_config())
    
    # Obtener HTML
    print("Obteniendo HTML con httpx...")
    result, html = httpx_service.get_html_sync(url)
    
    print(f"\nResultado:")
    print(f"  - Success: {result.get('success', False)}")
    print(f"  - Status Code: {result.get('status_code', 'N/A')}")
    print(f"  - Method: {result.get('method', 'N/A')}")
    print(f"  - Error: {result.get('error', 'None')}")
    print(f"  - HTML Length: {len(html)} caracteres")
    
    if html:
        # Parsear HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar título
        title = soup.find('title')
        print(f"\nTítulo de la página: {title.text.strip() if title else 'No encontrado'}")
        
        # Buscar meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            print(f"Meta description: {meta_desc.get('content', '')[:100]}...")
        
        # Contar headers
        print("\nConteo de headers:")
        for tag in ['h1', 'h2', 'h3']:
            count = len(soup.find_all(tag))
            print(f"  - {tag.upper()}: {count}")
            
            # Mostrar los primeros 3
            headers = soup.find_all(tag)
            if headers:
                print(f"    Ejemplos:")
                for i, h in enumerate(headers[:3]):
                    print(f"      {i+1}. {h.text.strip()[:60]}...")
    else:
        print("\nNo se obtuvo HTML!")

if __name__ == "__main__":
    test_one_url()
