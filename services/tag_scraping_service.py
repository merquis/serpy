"""
Servicio de Tag Scraping - Extracción de estructura HTML
Con optimización usando HTTPX primero y Playwright como fallback
"""
import asyncio
from typing import List, Dict, Any, Optional
import logging
from services.utils import PlaywrightService, PlaywrightConfig
from services.utils.httpx_service import HttpxService, create_stealth_httpx_config
from config import config

logger = logging.getLogger(__name__)

class TagScrapingService:
    """Servicio para extraer estructura jerárquica de etiquetas HTML"""
    
    def __init__(self):
        # Configuración específica para tag scraping con Playwright
        self.playwright_config = PlaywrightConfig(
            wait_until="networkidle",
            timeout=30000
        )
        self.playwright_service = PlaywrightService(self.playwright_config)
        
        # Configuración para HTTPX con medidas anti-bot
        self.httpx_config = create_stealth_httpx_config()
        self.httpx_service = HttpxService(self.httpx_config)
    
    async def scrape_tags_from_json(
        self,
        json_data: Any,
        max_concurrent: int = 5,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Extrae la estructura de etiquetas de URLs contenidas en JSON
        
        Args:
            json_data: Datos JSON con URLs (puede ser dict o list)
            max_concurrent: Número máximo de scrapers concurrentes
            progress_callback: Función callback para actualizar progreso
            
        Returns:
            Lista de resultados con estructura de etiquetas
        """
        # Convertir a lista si es necesario
        data_list = json_data if isinstance(json_data, list) else [json_data]
        all_results = []
        
        # Calcular total de URLs para progreso
        total_urls = 0
        for item in data_list:
            if isinstance(item, dict):
                total_urls += len(self._extract_urls_from_item(item))
        
        urls_processed = 0
        
        for item in data_list:
            if not isinstance(item, dict):
                continue
            
            # Extraer contexto
            context = {
                "busqueda": item.get("busqueda", ""),
                "idioma": item.get("idioma", ""),
                "region": item.get("region", ""),
                "dominio": item.get("dominio", ""),
                "url_busqueda": item.get("url_busqueda", "")
            }
            
            # Extraer URLs
            urls = self._extract_urls_from_item(item)
            
            if urls:
                # Función para procesar cada URL con HTTPX o navegador
                async def process_tag_structure(url: str, html: str, method_or_browser) -> Dict[str, Any]:
                    try:
                        # Si es string, es el método (httpx)
                        if isinstance(method_or_browser, str):
                            # Procesar con BeautifulSoup para httpx
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Extraer título
                            title_tag = soup.find('title')
                            title = title_tag.text.strip() if title_tag else ""
                            
                            # Extraer meta description
                            meta_desc = soup.find('meta', attrs={'name': 'description'})
                            description = meta_desc.get('content', '').strip() if meta_desc else ""
                            
                            # Extraer estructura completa de headings
                            h1_structure = self._extract_h1_structure_from_soup(soup)
                            
                            return {
                                "url": url,
                                "status_code": 200,
                                "title": title,
                                "description": description,
                                "h1": h1_structure,
                                "method": "httpx"  # Indicar que se usó httpx
                            }
                        else:
                            # Es un browser de Playwright
                            page = await method_or_browser.new_page()
                            try:
                                await page.set_content(html)
                                
                                # Extraer título
                                title = await page.title()
                                
                                # Extraer meta description
                                description = await page.evaluate("""
                                    () => {
                                        const metaDesc = document.querySelector('meta[name="description"]');
                                        return metaDesc ? metaDesc.content.trim() : "";
                                    }
                                """)
                                
                                # Extraer estructura del H1
                                h1_structure = await self.playwright_service.execute_javascript(
                                    page, 
                                    self._get_h1_structure_script()
                                )
                                
                                return {
                                    "url": url,
                                    "status_code": 200,
                                    "title": title,
                                    "description": description,
                                    "h1": h1_structure,
                                    "method": "playwright"  # Indicar que se usó Playwright
                                }
                            finally:
                                await page.close()
                    except Exception as e:
                        logger.error(f"Error procesando estructura de {url}: {e}")
                        return {
                            "url": url,
                            "status_code": "error",
                            "error": str(e),
                            "method": method_or_browser if isinstance(method_or_browser, str) else "playwright"
                        }
                
                # Crear callback personalizado
                def enhanced_progress_callback(info):
                    if progress_callback:
                        # Pasar información de progreso directamente
                        if isinstance(info, dict) and "active_urls" in info:
                            progress_callback(info)
                
                # Procesar URLs usando HTTPX con fallback a Playwright
                results = await self.httpx_service.process_urls_batch_with_fallback(
                    urls=urls,
                    process_func=process_tag_structure,
                    playwright_service=self.playwright_service,
                    config=self.httpx_config,
                    playwright_config=self.playwright_config,
                    max_concurrent=max_concurrent,
                    progress_callback=enhanced_progress_callback
                )
                
                urls_processed += len(urls)
                
                all_results.append({
                    **context,
                    "resultados": results
                })
        
        return all_results
    
    def _extract_urls_from_item(self, item: Dict[str, Any]) -> List[str]:
        """Extrae todas las URLs de un item del JSON"""
        urls = []
        
        # Buscar en campo 'urls'
        if "urls" in item:
            for url_item in item["urls"]:
                if isinstance(url_item, str):
                    urls.append(url_item)
                elif isinstance(url_item, dict) and "url" in url_item:
                    urls.append(url_item["url"])
        
        # Buscar en campo 'resultados'
        if "resultados" in item:
            for result in item["resultados"]:
                if isinstance(result, dict) and "url" in result:
                    urls.append(result["url"])
        
        return urls
    
    def _get_h1_structure_script(self) -> str:
        """Retorna el script JavaScript para extraer la estructura del primer H1 con su texto y H2/H3 anidados"""
        return """
            () => {
                // Función para obtener el texto limpio entre dos elementos
                function getTextBetweenElements(startElement, endElement) {
                    let text = '';
                    let currentNode = startElement.nextSibling;
                    
                    while (currentNode && currentNode !== endElement) {
                        if (currentNode.nodeType === Node.TEXT_NODE) {
                            text += currentNode.textContent;
                        } else if (currentNode.nodeType === Node.ELEMENT_NODE) {
                            // Ignorar scripts, estilos y elementos ocultos
                            const tagName = currentNode.tagName.toLowerCase();
                            if (tagName !== 'script' && tagName !== 'style' && 
                                !currentNode.classList.contains('hidden') &&
                                currentNode.style.display !== 'none') {
                                
                                // Para elementos que no son headings, obtener su texto
                                if (!['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) {
                                    text += currentNode.textContent;
                                }
                            }
                        }
                        currentNode = currentNode.nextSibling;
                    }
                    
                    // Limpiar el texto: eliminar espacios múltiples, saltos de línea excesivos
                    return text
                        .replace(/\\s+/g, ' ')
                        .replace(/\\n{3,}/g, '\\n\\n')
                        .trim()
                        .substring(0, 1000); // Limitar a 1000 caracteres
                }
                
                // Buscar el primer H1
                const firstH1 = document.querySelector('h1');
                if (!firstH1) {
                    return {};
                }
                
                // Obtener todos los headings
                const allHeadings = Array.from(document.querySelectorAll('h1, h2, h3'));
                
                // Encontrar el índice del primer H1
                const h1Index = allHeadings.indexOf(firstH1);
                
                // Obtener el texto del H1
                const h1Titulo = firstH1.textContent.trim();
                const nextHeadingAfterH1 = allHeadings[h1Index + 1] || null;
                const h1Texto = getTextBetweenElements(firstH1, nextHeadingAfterH1);
                
                // Estructura del H1
                const h1Structure = {
                    titulo: h1Titulo,
                    texto: h1Texto
                };
                
                // Lista temporal para h2s
                const h2List = [];
                let currentH2 = null;
                
                // Procesar todos los headings después del primer H1
                for (let i = h1Index + 1; i < allHeadings.length; i++) {
                    const heading = allHeadings[i];
                    const tagName = heading.tagName.toLowerCase();
                    
                    // Si encontramos otro H1, paramos
                    if (tagName === 'h1') {
                        break;
                    }
                    
                    // Obtener el siguiente heading para el texto
                    const nextHeading = allHeadings[i + 1] || null;
                    const headingText = getTextBetweenElements(heading, nextHeading);
                    
                    if (tagName === 'h2') {
                        // Si había un h2 anterior, procesarlo
                        if (currentH2) {
                            // Solo añadir h3 si tiene elementos
                            if (currentH2.h3Temp && currentH2.h3Temp.length > 0) {
                                currentH2.h3 = currentH2.h3Temp;
                            }
                            delete currentH2.h3Temp;
                            h2List.push(currentH2);
                        }
                        
                        currentH2 = {
                            titulo: heading.textContent.trim(),
                            texto: headingText,
                            h3Temp: []
                        };
                        
                    } else if (tagName === 'h3' && currentH2) {
                        const h3Item = {
                            titulo: heading.textContent.trim(),
                            texto: headingText
                        };
                        currentH2.h3Temp.push(h3Item);
                    }
                }
                
                // Añadir el último h2 si existe
                if (currentH2) {
                    if (currentH2.h3Temp && currentH2.h3Temp.length > 0) {
                        currentH2.h3 = currentH2.h3Temp;
                    }
                    delete currentH2.h3Temp;
                    h2List.push(currentH2);
                }
                
                // Solo añadir h2 a la estructura si hay elementos
                if (h2List.length > 0) {
                    h1Structure.h2 = h2List;
                }
                
                return h1Structure;
            }
        """
    
    def _get_heading_extraction_script(self) -> str:
        """Retorna el script JavaScript para extraer TODA la estructura de headings con su texto asociado"""
        return """
            () => {
                // Función para obtener el texto limpio entre dos elementos
                function getTextBetweenElements(startElement, endElement) {
                    let text = '';
                    let currentNode = startElement.nextSibling;
                    
                    while (currentNode && currentNode !== endElement) {
                        if (currentNode.nodeType === Node.TEXT_NODE) {
                            text += currentNode.textContent;
                        } else if (currentNode.nodeType === Node.ELEMENT_NODE) {
                            // Ignorar scripts, estilos y elementos ocultos
                            const tagName = currentNode.tagName.toLowerCase();
                            if (tagName !== 'script' && tagName !== 'style' && 
                                !currentNode.classList.contains('hidden') &&
                                currentNode.style.display !== 'none') {
                                
                                // Para elementos que no son headings, obtener su texto
                                if (!['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tagName)) {
                                    text += currentNode.textContent;
                                }
                            }
                        }
                        currentNode = currentNode.nextSibling;
                    }
                    
                    // Limpiar el texto: eliminar espacios múltiples, saltos de línea excesivos
                    return text
                        .replace(/\\s+/g, ' ')
                        .replace(/\\n{3,}/g, '\\n\\n')
                        .trim()
                        .substring(0, 1000); // Limitar a 1000 caracteres para evitar textos muy largos
                }
                
                // Obtener TODOS los headings de la página
                const allHeadings = Array.from(document.querySelectorAll('h1, h2, h3'));
                
                if (allHeadings.length === 0) {
                    return { headings: [], total_h1: 0, total_h2: 0, total_h3: 0 };
                }
                
                // Para cada heading, obtener su texto asociado
                const headingsWithText = allHeadings.map((heading, index) => {
                    const nextHeading = allHeadings[index + 1] || null;
                    const associatedText = getTextBetweenElements(heading, nextHeading);
                    
                    return {
                        element: heading,
                        tag: heading.tagName.toLowerCase(),
                        titulo: heading.textContent.trim(),
                        texto: associatedText,
                        level: parseInt(heading.tagName.charAt(1))
                    };
                });
                
                // Construir estructura jerárquica
                const result = {
                    headings: [],
                    total_h1: 0,
                    total_h2: 0,
                    total_h3: 0
                };
                
                let currentH1 = null;
                let currentH2 = null;
                
                headingsWithText.forEach(heading => {
                    if (heading.tag === 'h1') {
                        currentH1 = {
                            titulo: heading.titulo,
                            texto: heading.texto,
                            level: 'h1',
                            h2: []
                        };
                        currentH2 = null;
                        result.headings.push(currentH1);
                        result.total_h1++;
                    } else if (heading.tag === 'h2') {
                        currentH2 = {
                            titulo: heading.titulo,
                            texto: heading.texto,
                            level: 'h2',
                            h3: []
                        };
                        
                        if (currentH1) {
                            currentH1.h2.push(currentH2);
                        } else {
                            // H2 sin H1 padre, crear estructura independiente
                            result.headings.push({
                                titulo: '[Sin H1]',
                                texto: '',
                                level: 'h1',
                                h2: [currentH2]
                            });
                        }
                        result.total_h2++;
                    } else if (heading.tag === 'h3') {
                        const h3Item = {
                            titulo: heading.titulo,
                            texto: heading.texto,
                            level: 'h3'
                        };
                        
                        if (currentH2) {
                            currentH2.h3.push(h3Item);
                        } else if (currentH1) {
                            // H3 sin H2 padre pero con H1
                            currentH2 = {
                                titulo: '[Sin H2]',
                                texto: '',
                                level: 'h2',
                                h3: [h3Item]
                            };
                            currentH1.h2.push(currentH2);
                        } else {
                            // H3 sin H1 ni H2 padre
                            result.headings.push({
                                titulo: '[Sin H1]',
                                texto: '',
                                level: 'h1',
                                h2: [{
                                    titulo: '[Sin H2]',
                                    texto: '',
                                    level: 'h2',
                                    h3: [h3Item]
                                }]
                            });
                        }
                        result.total_h3++;
                    }
                });
                
                return result;
            }
        """
    
    def _extract_h1_structure_from_soup(self, soup) -> Dict[str, Any]:
        """Extrae la estructura del primer H1 con todos sus H2 y H3 anidados"""
        import re
        
        # Buscar el primer H1
        first_h1 = soup.find('h1')
        if not first_h1:
            return {}
        
        # Obtener todos los headings de la página
        all_headings = soup.find_all(['h1', 'h2', 'h3'])
        
        # Encontrar el índice del primer H1
        h1_index = all_headings.index(first_h1)
        
        # Función para obtener texto entre dos elementos
        def get_text_between_headings(current_heading, next_heading):
            """Extrae el texto entre dos headings"""
            text_parts = []
            
            # Obtener todos los elementos siguientes hasta el próximo heading
            current = current_heading.next_sibling
            while current and current != next_heading:
                if hasattr(current, 'name'):
                    # Es un elemento HTML
                    if current.name not in ['script', 'style', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'noscript']:
                        # Ignorar elementos ocultos
                        if current.get('style') and 'display:none' in current.get('style'):
                            current = current.next_sibling
                            continue
                        
                        # Ignorar elementos que típicamente no contienen texto relevante
                        if current.name in ['img', 'iframe', 'video', 'audio', 'canvas', 'svg']:
                            current = current.next_sibling
                            continue
                        
                        # Obtener texto del elemento
                        element_text = current.get_text(strip=True)
                        if element_text:
                            text_parts.append(element_text)
                elif isinstance(current, str):
                    # Es un nodo de texto
                    text = current.strip()
                    if text:
                        text_parts.append(text)
                
                current = current.next_sibling
            
            # Unir y limpiar el texto
            full_text = ' '.join(text_parts)
            # Eliminar espacios múltiples y saltos de línea excesivos
            full_text = re.sub(r'\s+', ' ', full_text)
            # Eliminar caracteres HTML que puedan quedar
            full_text = re.sub(r'<[^>]+>', '', full_text)
            # Eliminar entidades HTML comunes
            full_text = full_text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            # Limitar longitud
            return full_text[:1000].strip()
        
        # Obtener el texto del H1
        h1_titulo = first_h1.get_text(strip=True)
        
        # Encontrar el siguiente heading después del H1 para obtener su texto
        next_heading_after_h1 = all_headings[h1_index + 1] if h1_index + 1 < len(all_headings) else None
        h1_texto = get_text_between_headings(first_h1, next_heading_after_h1)
        
        # Estructura del H1
        h1_structure = {
            "titulo": h1_titulo,
            "texto": h1_texto
        }
        
        # Lista temporal para h2s
        h2_list = []
        current_h2 = None
        
        # Procesar todos los headings después del primer H1
        for i in range(h1_index + 1, len(all_headings)):
            heading = all_headings[i]
            tag_name = heading.name.lower()
            
            # Si encontramos otro H1, paramos
            if tag_name == 'h1':
                break
            
            # Obtener el siguiente heading para el texto
            next_heading = all_headings[i + 1] if i + 1 < len(all_headings) else None
            heading_text = get_text_between_headings(heading, next_heading)
            
            if tag_name == 'h2':
                # Si había un h2 anterior, añadirlo a la lista
                if current_h2:
                    # Solo añadir h3 si tiene elementos
                    if not current_h2.get('h3_temp'):
                        current_h2.pop('h3_temp', None)
                    else:
                        current_h2['h3'] = current_h2.pop('h3_temp')
                    h2_list.append(current_h2)
                
                current_h2 = {
                    "titulo": heading.get_text(strip=True),
                    "texto": heading_text,
                    "h3_temp": []  # Lista temporal
                }
                
            elif tag_name == 'h3' and current_h2:
                h3_item = {
                    "titulo": heading.get_text(strip=True),
                    "texto": heading_text
                }
                current_h2["h3_temp"].append(h3_item)
        
        # Añadir el último h2 si existe
        if current_h2:
            if not current_h2.get('h3_temp'):
                current_h2.pop('h3_temp', None)
            else:
                current_h2['h3'] = current_h2.pop('h3_temp')
            h2_list.append(current_h2)
        
        # Solo añadir h2 a la estructura si hay elementos
        if h2_list:
            h1_structure["h2"] = h2_list
        
        return h1_structure
    
    def _extract_headings_from_soup(self, soup) -> Dict[str, Any]:
        """Extrae TODA la estructura de headings usando BeautifulSoup con texto asociado"""
        import re
        
        # Obtener TODOS los headings de la página
        all_headings = soup.find_all(['h1', 'h2', 'h3'])
        
        if not all_headings:
            return {"headings": [], "total_h1": 0, "total_h2": 0, "total_h3": 0}
        
        # Función para obtener texto entre dos elementos
        def get_text_between_headings(current_heading, next_heading):
            """Extrae el texto entre dos headings"""
            text_parts = []
            
            # Obtener todos los elementos siguientes hasta el próximo heading
            current = current_heading.next_sibling
            while current and current != next_heading:
                if hasattr(current, 'name'):
                    # Es un elemento HTML
                    if current.name not in ['script', 'style', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        # Ignorar elementos ocultos
                        if current.get('style') and 'display:none' in current.get('style'):
                            current = current.next_sibling
                            continue
                        
                        # Obtener texto del elemento
                        element_text = current.get_text(strip=True)
                        if element_text:
                            text_parts.append(element_text)
                elif isinstance(current, str):
                    # Es un nodo de texto
                    text = current.strip()
                    if text:
                        text_parts.append(text)
                
                current = current.next_sibling
            
            # Unir y limpiar el texto
            full_text = ' '.join(text_parts)
            # Eliminar espacios múltiples
            full_text = re.sub(r'\s+', ' ', full_text)
            # Limitar longitud
            return full_text[:1000].strip()
        
        # Procesar cada heading con su texto asociado
        headings_with_text = []
        for i, heading in enumerate(all_headings):
            next_heading = all_headings[i + 1] if i + 1 < len(all_headings) else None
            associated_text = get_text_between_headings(heading, next_heading)
            
            headings_with_text.append({
                'tag': heading.name.lower(),
                'titulo': heading.get_text(strip=True),
                'texto': associated_text
            })
        
        # Construir estructura jerárquica
        result = {
            "headings": [],
            "total_h1": 0,
            "total_h2": 0,
            "total_h3": 0
        }
        
        current_h1 = None
        current_h2 = None
        
        for heading_data in headings_with_text:
            tag_name = heading_data['tag']
            titulo = heading_data['titulo']
            texto = heading_data['texto']
            
            if tag_name == 'h1':
                current_h1 = {
                    "titulo": titulo,
                    "texto": texto,
                    "level": "h1",
                    "h2": []
                }
                current_h2 = None
                result["headings"].append(current_h1)
                result["total_h1"] += 1
                
            elif tag_name == 'h2':
                current_h2 = {
                    "titulo": titulo,
                    "texto": texto,
                    "level": "h2",
                    "h3": []
                }
                
                if current_h1:
                    current_h1["h2"].append(current_h2)
                else:
                    # H2 sin H1 padre, crear estructura independiente
                    result["headings"].append({
                        "titulo": "[Sin H1]",
                        "texto": "",
                        "level": "h1",
                        "h2": [current_h2]
                    })
                result["total_h2"] += 1
                
            elif tag_name == 'h3':
                h3_item = {
                    "titulo": titulo,
                    "texto": texto,
                    "level": "h3"
                }
                
                if current_h2:
                    current_h2["h3"].append(h3_item)
                elif current_h1:
                    # H3 sin H2 padre pero con H1
                    current_h2 = {
                        "titulo": "[Sin H2]",
                        "texto": "",
                        "level": "h2",
                        "h3": [h3_item]
                    }
                    current_h1["h2"].append(current_h2)
                else:
                    # H3 sin H1 ni H2 padre
                    result["headings"].append({
                        "titulo": "[Sin H1]",
                        "texto": "",
                        "level": "h1",
                        "h2": [{
                            "titulo": "[Sin H2]",
                            "texto": "",
                            "level": "h2",
                            "h3": [h3_item]
                        }]
                    })
                result["total_h3"] += 1
        
        return result
