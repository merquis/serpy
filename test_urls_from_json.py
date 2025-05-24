"""
Script de prueba usando las URLs específicas del JSON proporcionado por el usuario
"""
from services.scraping_service import TagScrapingService
from services.utils.httpx_service import HttpxService, create_fast_httpx_config
import json

def test_urls_from_json():
    """Prueba las URLs específicas del JSON del usuario"""
    
    # URLs del JSON proporcionado
    urls = [
        "https://www.tripadvisor.es/Hotels-g187441-Granada_Province_of_Granada_Andalucia-Hotels.html",
        "https://destinia.com/guides/10-mejores-hoteles-en-granada-por-calidad-y-precio/",
        "https://www.booking.com/city/es/granada.es.html",
        "https://es.luxuryhotel.world/granada-spain/",
        "https://www.ideal.es/granada/mejores-hoteles-granada-segun-the-times-20230510141806-nt.html",
        "https://www.tripadvisor.es/Hotels-g187441-zff12-Granada_Province_of_Granada_Andalucia-Hotels.html",
        "https://elpais.com/escaparate/viajes/2025-02-26/mejores-hoteles-granada.html",
        "https://andaluciavibes.com/hoteles/granada/centro/",
        "https://comeamaviaja.com/hoteles-con-encanto-en-granada/",
        "https://www.booking.com/reviews/es/city/granada.es.html"
    ]
    
    print(f"Probando {len(urls)} URLs del JSON del usuario...\n")
    print("="*80)
    
    # Crear servicio
    tag_service = TagScrapingService()
    
    # Procesar todas las URLs
    results = tag_service.scrape_tags_from_urls(urls, extract_content=False)
    
    # Estadísticas
    successful = 0
    failed = 0
    with_title = 0
    with_h1 = 0
    with_headers = 0
    
    # Mostrar resultados detallados
    for i, result in enumerate(results):
        print(f"\n{'='*60}")
        print(f"URL {i+1}: {result.get('url')}")
        print(f"Status Code: {result.get('status_code')}")
        print(f"Método: {result.get('method', 'N/A')}")
        
        if result.get('error'):
            print(f"❌ ERROR: {result.get('error')}")
            print(f"   Necesita Playwright: {result.get('needs_playwright', False)}")
            failed += 1
        else:
            successful += 1
            
            # Título
            title = result.get('title', '')
            if title:
                with_title += 1
                print(f"✅ Título: {title[:80]}...")
            else:
                print("❌ Título: No encontrado")
            
            # Descripción
            desc = result.get('description', '')
            if desc:
                print(f"✅ Descripción: {desc[:80]}...")
            
            # Headers
            h1_data = result.get('h1', {})
            if h1_data:
                if 'headers' in h1_data:
                    # Caso donde no hay estructura H1 pero sí otros headers
                    headers_count = len(h1_data['headers'])
                    if headers_count > 0:
                        with_headers += 1
                        print(f"✅ Headers encontrados: {headers_count}")
                        # Contar por tipo
                        h1_count = sum(1 for h in h1_data['headers'] if h['level'] == 'h1')
                        h2_count = sum(1 for h in h1_data['headers'] if h['level'] == 'h2')
                        h3_count = sum(1 for h in h1_data['headers'] if h['level'] == 'h3')
                        print(f"   - H1: {h1_count}, H2: {h2_count}, H3: {h3_count}")
                        
                        # Mostrar algunos ejemplos
                        for j, header in enumerate(h1_data['headers'][:3]):
                            print(f"   - {header['level']}: {header['text'][:60]}...")
                        if headers_count > 3:
                            print(f"   ... y {headers_count - 3} headers más")
                else:
                    # Caso con estructura H1 normal
                    if h1_data.get('titulo'):
                        with_h1 += 1
                        with_headers += 1
                        print(f"✅ H1: {h1_data.get('titulo', '')[:80]}...")
                        h2_count = len(h1_data.get('h2', []))
                        if h2_count > 0:
                            print(f"   - H2 encontrados: {h2_count}")
                            for h2 in h1_data.get('h2', [])[:2]:
                                print(f"     • {h2.get('titulo', '')[:60]}...")
                                h3_count = len(h2.get('h3', []))
                                if h3_count > 0:
                                    print(f"       - H3 encontrados: {h3_count}")
            else:
                print("❌ Headers: No encontrados")
    
    # Resumen final
    print(f"\n{'='*80}")
    print("RESUMEN DE RESULTADOS:")
    print(f"Total URLs procesadas: {len(urls)}")
    print(f"✅ Exitosas: {successful} ({successful/len(urls)*100:.1f}%)")
    print(f"❌ Fallidas: {failed} ({failed/len(urls)*100:.1f}%)")
    print(f"\nDe las exitosas:")
    print(f"  - Con título: {with_title} ({with_title/max(successful,1)*100:.1f}%)")
    print(f"  - Con headers: {with_headers} ({with_headers/max(successful,1)*100:.1f}%)")
    print(f"  - Con H1 estructurado: {with_h1}")
    
    # Análisis de métodos usados
    methods = {}
    for result in results:
        method = result.get('method', 'unknown')
        methods[method] = methods.get(method, 0) + 1
    
    print(f"\nMétodos utilizados:")
    for method, count in methods.items():
        print(f"  - {method}: {count}")
    
    # URLs que necesitan Playwright
    playwright_needed = [r['url'] for r in results if r.get('needs_playwright')]
    if playwright_needed:
        print(f"\nURLs que necesitan Playwright ({len(playwright_needed)}):")
        for url in playwright_needed:
            print(f"  - {url}")

if __name__ == "__main__":
    try:
        test_urls_from_json()
    except Exception as e:
        print(f"Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
