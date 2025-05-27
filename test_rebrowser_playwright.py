"""
Script de prueba para rebrowser-playwright
Demuestra cómo usar el servicio para evitar detección de bots
"""
import asyncio
import sys
from services.utils.rebrowser_playwright_service import (
    RebrowserPlaywrightService,
    create_stealth_config,
    create_mobile_config,
    create_fast_stealth_config
)


async def test_bot_detection():
    """Prueba el servicio contra sitios de detección de bots"""
    print("=== Prueba de Detección de Bots con Rebrowser-Playwright ===\n")
    
    # URLs de prueba para detección de bots
    test_urls = [
        "https://bot.sannysoft.com/",  # Test general de detección
        "https://arh.antoinevastel.com/bots/areyouheadless",  # Test de headless
        "https://fingerprint.com/demo/",  # Fingerprinting avanzado
        "https://pixelscan.net/",  # Scanner de pixels
    ]
    
    # Configuración stealth
    config = create_stealth_config(headless=False)  # Mejor en modo no-headless
    service = RebrowserPlaywrightService(config)
    
    print("Configuración:")
    print(f"- User Agent: {config.user_agent}")
    print(f"- Viewport: {config.viewport}")
    print(f"- Headless: {config.headless}")
    print(f"- Browser: {config.default_browser_type}\n")
    
    # Probar cada URL
    for url in test_urls:
        print(f"\nProbando: {url}")
        print("-" * 50)
        
        try:
            result, html = await service.get_html_simple(url)
            
            if result.get("success"):
                print(f"✅ Éxito - HTML obtenido: {result['html_length']} caracteres")
                print(f"   Status code: {result['status_code']}")
                
                # Buscar indicadores comunes de detección
                if "bot" in html.lower() and "detected" in html.lower():
                    print("⚠️  Posible detección de bot encontrada en el HTML")
                elif "human" in html.lower() or "passed" in html.lower():
                    print("✅ Parece que pasó la prueba de detección")
                    
            else:
                print(f"❌ Error: {result.get('error')}")
                print(f"   Detalles: {result.get('details')}")
                
        except Exception as e:
            print(f"❌ Excepción: {str(e)}")
        
        # Pequeña pausa entre pruebas
        await asyncio.sleep(2)


async def test_real_world_sites():
    """Prueba con sitios web reales que suelen tener protección anti-bot"""
    print("\n\n=== Prueba con Sitios Web Reales ===\n")
    
    # Sitios con protección anti-bot conocida
    protected_sites = [
        {
            "url": "https://www.amazon.es/",
            "name": "Amazon",
            "check_selector": "#nav-logo"
        },
        {
            "url": "https://www.linkedin.com/",
            "name": "LinkedIn", 
            "check_selector": ".nav__logo"
        },
        {
            "url": "https://www.airbnb.es/",
            "name": "Airbnb",
            "check_selector": "[data-testid='header-logo']"
        }
    ]
    
    # Usar configuración móvil para algunos sitios
    configs = [
        ("Desktop Stealth", create_stealth_config()),
        ("Mobile iPhone", create_mobile_config("iPhone 13")),
        ("Fast Stealth", create_fast_stealth_config())
    ]
    
    for config_name, config in configs:
        print(f"\n--- Probando con configuración: {config_name} ---")
        service = RebrowserPlaywrightService(config)
        
        for site in protected_sites[:1]:  # Solo probar el primer sitio por configuración
            print(f"\nAccediendo a {site['name']} ({site['url']})")
            
            try:
                result, html = await service.get_html_simple(site['url'])
                
                if result.get("success"):
                    print(f"✅ Página cargada exitosamente")
                    print(f"   HTML length: {result['html_length']}")
                    
                    # Verificar si el selector esperado está presente
                    if site['check_selector'] in html:
                        print(f"✅ Selector '{site['check_selector']}' encontrado")
                    else:
                        print(f"⚠️  Selector '{site['check_selector']}' no encontrado")
                    
                    # Buscar señales de bloqueo
                    blocked_keywords = ["captcha", "blocked", "denied", "forbidden", "robot"]
                    found_blocks = [kw for kw in blocked_keywords if kw in html.lower()]
                    
                    if found_blocks:
                        print(f"⚠️  Posibles señales de bloqueo encontradas: {found_blocks}")
                    else:
                        print("✅ No se encontraron señales obvias de bloqueo")
                        
                else:
                    print(f"❌ Error al cargar: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ Excepción: {str(e)}")
            
            await asyncio.sleep(3)  # Pausa entre sitios


async def test_javascript_execution():
    """Prueba la ejecución de JavaScript en páginas"""
    print("\n\n=== Prueba de Ejecución de JavaScript ===\n")
    
    from playwright.async_api import async_playwright
    
    config = create_stealth_config()
    service = RebrowserPlaywrightService(config)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=config.headless,
            args=config.browser_args
        )
        
        try:
            context = await service._create_context(browser)
            page = await context.new_page()
            
            # Navegar a una página de prueba
            await page.goto("https://example.com")
            
            # Ejecutar varios scripts de prueba
            tests = [
                ("Navigator properties", "Object.keys(navigator).length"),
                ("Chrome object", "typeof window.chrome"),
                ("Webdriver property", "navigator.webdriver"),
                ("Plugins length", "navigator.plugins.length"),
                ("Languages", "navigator.languages.join(', ')"),
                ("User Agent", "navigator.userAgent"),
                ("Screen resolution", "`${screen.width}x${screen.height}`"),
                ("Color depth", "screen.colorDepth"),
                ("Timezone", "Intl.DateTimeFormat().resolvedOptions().timeZone")
            ]
            
            print("Propiedades del navegador detectadas:\n")
            for test_name, script in tests:
                try:
                    result = await service.execute_javascript(page, script)
                    print(f"{test_name}: {result}")
                except Exception as e:
                    print(f"{test_name}: Error - {str(e)}")
            
            await page.close()
            await context.close()
            
        finally:
            await browser.close()


async def test_batch_processing():
    """Prueba el procesamiento en lote con comportamiento humano"""
    print("\n\n=== Prueba de Procesamiento en Lote ===\n")
    
    urls = [
        "https://httpbin.org/user-agent",
        "https://httpbin.org/headers",
        "https://httpbin.org/ip"
    ]
    
    config = create_stealth_config()
    service = RebrowserPlaywrightService(config)
    
    async def extract_json(url: str, html: str, browser) -> dict:
        """Extrae JSON del HTML de httpbin"""
        try:
            # httpbin devuelve JSON en etiquetas <pre>
            start = html.find("<pre>") + 5
            end = html.find("</pre>")
            if start > 4 and end > start:
                import json
                json_str = html[start:end]
                return {
                    "url": url,
                    "success": True,
                    "data": json.loads(json_str)
                }
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    print("Procesando URLs con delays humanos...")
    print(f"URLs a procesar: {len(urls)}")
    print(f"Concurrencia máxima: 2")
    print(f"Delay entre requests: 2-5 segundos\n")
    
    results = await service.process_urls_batch(
        urls,
        extract_json,
        max_concurrent=2,
        delay_between_requests=(2.0, 5.0)
    )
    
    for result in results:
        if isinstance(result, dict) and result.get("success"):
            print(f"\n✅ {result['url']}")
            if "data" in result:
                for key, value in result["data"].items():
                    print(f"   {key}: {value}")
        else:
            print(f"\n❌ Error en resultado: {result}")


async def main():
    """Ejecuta todas las pruebas"""
    
    # Menú de opciones
    print("\n🤖 Pruebas de Rebrowser-Playwright Anti-Detección\n")
    print("1. Prueba de detección de bots")
    print("2. Prueba con sitios web reales")
    print("3. Prueba de ejecución de JavaScript")
    print("4. Prueba de procesamiento en lote")
    print("5. Ejecutar todas las pruebas")
    print("0. Salir\n")
    
    choice = input("Selecciona una opción (0-5): ").strip()
    
    if choice == "1":
        await test_bot_detection()
    elif choice == "2":
        await test_real_world_sites()
    elif choice == "3":
        await test_javascript_execution()
    elif choice == "4":
        await test_batch_processing()
    elif choice == "5":
        await test_bot_detection()
        await test_real_world_sites()
        await test_javascript_execution()
        await test_batch_processing()
    elif choice == "0":
        print("¡Hasta luego!")
        sys.exit(0)
    else:
        print("Opción no válida")


if __name__ == "__main__":
    # Configurar logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar pruebas
    asyncio.run(main())
