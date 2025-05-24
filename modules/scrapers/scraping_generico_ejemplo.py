"""
Ejemplo de scraper genérico usando el módulo reutilizable de Playwright
Este archivo demuestra cómo usar playwright_utils.py para crear nuevos scrapers
"""

import streamlit as st
import asyncio
from bs4 import BeautifulSoup
from modules.utils.playwright_utils import (
    PlaywrightConfig,
    obtener_html_simple,
    procesar_urls_en_lote,
    crear_config_generica
)


async def obtener_datos_pagina_generica(url: str) -> tuple:
    """
    Ejemplo de función para obtener datos de cualquier página web.
    
    Args:
        url: URL de la página a scrapear
        
    Returns:
        Tupla con (datos_extraidos, html_content)
    """
    # Crear configuración personalizada
    # Puedes ajustar estos parámetros según la página que quieras scrapear
    config = PlaywrightConfig(
        wait_for_selector="body",  # Esperar a que el body esté cargado
        timeout=30000,  # 30 segundos de timeout
        wait_until="domcontentloaded"  # Esperar solo a que el DOM esté cargado
    )
    
    # También puedes usar la función helper para crear una config
    # config = crear_config_generica(wait_for_selector="h1", timeout=45000)
    
    # Obtener HTML usando el módulo reutilizable
    resultado, html = await obtener_html_simple(url, config)
    
    # Si hay error, retornar el error
    if resultado.get("error"):
        return resultado, ""
    
    # Parsear el HTML con BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    
    # Extraer datos básicos como ejemplo
    datos_extraidos = {
        "url_original": url,
        "titulo": soup.find("title").text if soup.find("title") else "Sin título",
        "h1": soup.find("h1").text if soup.find("h1") else "Sin H1",
        "meta_description": "",
        "num_imagenes": len(soup.find_all("img")),
        "num_enlaces": len(soup.find_all("a")),
        "parrafos": [p.text.strip() for p in soup.find_all("p")[:5]]  # Primeros 5 párrafos
    }
    
    # Extraer meta description si existe
    meta_desc = soup.find("meta", {"name": "description"})
    if meta_desc:
        datos_extraidos["meta_description"] = meta_desc.get("content", "")
    
    return datos_extraidos, html


async def procesar_multiples_paginas(urls: list) -> list:
    """
    Procesa múltiples páginas web en lote.
    
    Args:
        urls: Lista de URLs para procesar
        
    Returns:
        Lista de resultados
    """
    # Configuración para procesamiento en lote
    config = PlaywrightConfig(
        wait_for_selector="body",
        timeout=30000,
        headless=True  # Ejecutar en modo headless para mejor rendimiento
    )
    
    # Procesar todas las URLs (máximo 3 concurrentes para no sobrecargar)
    resultados_html = await procesar_urls_en_lote(urls, config, max_concurrent=3)
    
    final_results = []
    
    for resultado, html in resultados_html:
        if resultado.get("error"):
            final_results.append(resultado)
        elif html:
            soup = BeautifulSoup(html, "html.parser")
            
            # Extraer datos básicos
            datos = {
                "url_original": resultado["url_original"],
                "titulo": soup.find("title").text if soup.find("title") else "Sin título",
                "h1": soup.find("h1").text if soup.find("h1") else "Sin H1",
                "longitud_html": len(html),
                "exito": True
            }
            final_results.append(datos)
    
    return final_results


# ════════════════════════════════════════════════════
# 🎯 Interfaz de Streamlit para demostración
# ════════════════════════════════════════════════════
def render_scraping_generico():
    st.title("🌐 Scraper Genérico con Playwright Reutilizable")
    
    st.markdown("""
    ### Ejemplo de uso del módulo `playwright_utils.py`
    
    Este scraper demuestra cómo reutilizar el código de Playwright para crear nuevos scrapers.
    Puedes usar este ejemplo como base para crear scrapers para otras páginas web.
    """)
    
    # Opción 1: Scraping de una sola URL
    st.subheader("📄 Scraping de URL Individual")
    
    url_individual = st.text_input(
        "Ingresa una URL para scrapear:",
        value="https://example.com"
    )
    
    if st.button("🔍 Scrapear URL Individual"):
        with st.spinner("Obteniendo datos..."):
            datos, html = asyncio.run(obtener_datos_pagina_generica(url_individual))
        
        if datos.get("error"):
            st.error(f"Error: {datos['error']} - {datos.get('details', '')}")
        else:
            st.success("✅ Datos obtenidos exitosamente")
            st.json(datos)
            
            if html:
                st.download_button(
                    "⬇️ Descargar HTML",
                    data=html.encode("utf-8"),
                    file_name="pagina_scrapeada.html",
                    mime="text/html"
                )
    
    # Opción 2: Scraping de múltiples URLs
    st.subheader("📚 Scraping de Múltiples URLs")
    
    urls_multiples = st.text_area(
        "Ingresa varias URLs (una por línea):",
        value="https://example.com\nhttps://example.org",
        height=100
    )
    
    if st.button("🔍 Scrapear Múltiples URLs"):
        urls = [url.strip() for url in urls_multiples.split("\n") if url.strip()]
        
        if urls:
            with st.spinner(f"Procesando {len(urls)} URLs..."):
                resultados = asyncio.run(procesar_multiples_paginas(urls))
            
            st.success(f"✅ Procesadas {len(resultados)} URLs")
            
            # Mostrar resultados en tabla
            for i, resultado in enumerate(resultados):
                with st.expander(f"Resultado {i+1}: {resultado.get('url_original', 'URL')}"):
                    st.json(resultado)
    
    # Sección de ayuda
    with st.expander("💡 Cómo adaptar este código para tu scraper"):
        st.markdown("""
        ### Pasos para crear tu propio scraper:
        
        1. **Importa las utilidades de Playwright:**
        ```python
        from modules.utils.playwright_utils import (
            PlaywrightConfig,
            obtener_html_simple,
            procesar_urls_en_lote
        )
        ```
        
        2. **Configura según tus necesidades:**
        ```python
        config = PlaywrightConfig(
            wait_for_selector="#mi-selector",  # Selector específico de tu página
            timeout=45000,  # Ajusta el timeout según necesites
            wait_until="networkidle"  # O "domcontentloaded" para páginas más rápidas
        )
        ```
        
        3. **Obtén el HTML:**
        ```python
        resultado, html = await obtener_html_simple(url, config)
        ```
        
        4. **Parsea con BeautifulSoup:**
        ```python
        soup = BeautifulSoup(html, "html.parser")
        # Extrae los datos que necesites
        ```
        
        ### Configuraciones disponibles:
        - `headless`: True/False (modo sin ventana)
        - `timeout`: Tiempo máximo de espera en ms
        - `wait_until`: "load", "domcontentloaded", "networkidle"
        - `user_agent`: Personaliza el User-Agent
        - `wait_for_selector`: Espera a que aparezca un elemento específico
        - `extra_headers`: Headers HTTP adicionales
        """)


if __name__ == "__main__":
    render_scraping_generico()
