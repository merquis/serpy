"""
Script de prueba directo sin dependencias de Streamlit
"""
import httpx
from bs4 import BeautifulSoup
import time
import random

def test_direct_httpx():
    """Prueba directa con httpx sin usar los servicios"""
    
    # URLs de prueba
    test_urls = [
        "https://destinia.com/guides/10-mejores-hoteles-en-granada-por-calidad-y-precio/",
        "https://www.booking.com/city/es/granada.es.html",
        "https://es.luxuryhotel.world/granada-spain/"
    ]
    
    # Headers para parecer un navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    print("Probando httpx directamente con las URLs del usuario...")
    print("=" * 80)
    
    for i, url in enumerate(test_urls):
        print(f"\n{i+1}. Probando: {url}")
        print("-" * 60)
        
        try:
            # Pequeño delay aleatorio entre requests
            if i > 0:
                delay = random.uniform(0.5, 1.5)
                print(f"   Esperando {delay:.1f} segundos...")
                time.sleep(delay)
            
            # Hacer la petición
            with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
                response = client.get(url)
                
                print(f"   Status Code: {response.status_code}")
                print(f"   Content Length: {len(response.text)} caracteres")
                
                if response.status_code == 200:
                    # Parsear HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Título
                    title = soup.find('title')
                    if title:
                        print(f"   ✅ Título: {title.text.strip()[:80]}...")
                    else:
                        print("   ❌ Título: No encontrado")
                    
                    # Meta description
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    if meta_desc:
                        content = meta_desc.get('content', '')
                        if content:
                            print(f"   ✅ Description: {content[:80]}...")
                    
                    # Contar headers
                    h1_count = len(soup.find_all('h1'))
                    h2_count = len(soup.find_all('h2'))
                    h3_count = len(soup.find_all('h3'))
                    
                    print(f"   📊 Headers encontrados: H1={h1_count}, H2={h2_count}, H3={h3_count}")
                    
                    # Mostrar algunos ejemplos
                    if h1_count > 0:
                        h1 = soup.find('h1')
                        print(f"      Primer H1: {h1.text.strip()[:60]}...")
                    
                    if h2_count > 0:
                        h2_list = soup.find_all('h2')[:3]
                        print(f"      Primeros H2:")
                        for j, h2 in enumerate(h2_list):
                            print(f"        {j+1}. {h2.text.strip()[:50]}...")
                    
                    # Verificar si parece estar bloqueado
                    text_lower = response.text.lower()
                    if any(indicator in text_lower for indicator in ['cloudflare', 'captcha', 'javascript is required']):
                        print("   ⚠️  ADVERTENCIA: Posible bloqueo detectado")
                else:
                    print(f"   ❌ Error HTTP: {response.status_code}")
                    
        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
    
    print("\n" + "=" * 80)
    print("Prueba completada!")

if __name__ == "__main__":
    test_direct_httpx()
