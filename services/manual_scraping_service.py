"""
Servicio de Scraping Manual de URLs
"""
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import logging
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.utils.httpx_service import httpx_requests, HttpxConfig, create_fast_httpx_config
import httpx

logger = logging.getLogger(__name__)

class ManualScrapingService:
    """Servicio para extraer etiquetas SEO de URLs manualmente introducidas"""
    
    def __init__(self):
        # Usar configuración rápida de httpx
        self.httpx_config = create_fast_httpx_config()
        self.httpx_service = httpx_requests
    
    def scrape_urls(
        self,
        urls: List[str],
        tags: List[str],
        max_workers: int = 5,
        timeout: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Extrae etiquetas SEO de múltiples URLs
        
        Args:
            urls: Lista de URLs a procesar
            tags: Lista de etiquetas a extraer
            max_workers: Número máximo de workers concurrentes
            timeout: Timeout para cada petición
            
        Returns:
            Lista de resultados con las etiquetas extraídas
        """
        results = []
        total_urls = len(urls)
        
        # Usar ThreadPoolExecutor para paralelismo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Crear futures para cada URL
            future_to_url = {
                executor.submit(self._scrape_single_url, url, tags, timeout): url
                for url in urls
            }
            
            # Procesar resultados conforme se completan
            for i, future in enumerate(as_completed(future_to_url)):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Actualizar progreso
                    progress = (i + 1) / total_urls
                    logger.info(f"Procesadas {i + 1}/{total_urls} URLs ({progress*100:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"Error procesando {url}: {e}")
                    results.append({
                        "url": url,
                        "status_code": "error",
                        "error": str(e)
                    })
        
        return results
    
    def _scrape_single_url(
        self,
        url: str,
        tags: List[str],
        timeout: int = 20
    ) -> Dict[str, Any]:
        """
        Extrae etiquetas de una única URL
        
        Args:
            url: URL a procesar
            tags: Lista de etiquetas a extraer
            timeout: Timeout para la petición
            
        Returns:
            Diccionario con los resultados
        """
        result = {"url": url}
        
        try:
            # Realizar petición HTTP con httpx
            response = self.httpx_service.get(url, timeout=timeout)
            result["status_code"] = response.status_code
            
            # Procesar solo si la respuesta es exitosa
            if response.status_code != 200:
                # Si httpx detecta que necesita Playwright, incluir esa información
                if hasattr(response, '_result') and response._result.get('needs_playwright'):
                    result["needs_playwright"] = True
                    result["error"] = response._result.get('details', 'Necesita Playwright')
                return result
            
            # Parsear HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extraer cada etiqueta solicitada
            if "title" in tags:
                result["title"] = self._extract_title(soup)
            
            if "description" in tags:
                result["description"] = self._extract_description(soup)
            
            if "h1" in tags:
                result["h1"] = self._extract_h1(soup)
            
            if "h2" in tags:
                result["h2"] = self._extract_h2_list(soup)
            
            if "h3" in tags:
                result["h3"] = self._extract_h3_list(soup)
            
            if "canonical" in tags:
                result["canonical"] = self._extract_canonical(soup)
            
            if "og:title" in tags:
                result["og:title"] = self._extract_og_title(soup)
            
            if "og:description" in tags:
                result["og:description"] = self._extract_og_description(soup)
            
        except httpx.TimeoutException:
            result["status_code"] = "timeout"
            result["error"] = f"Timeout después de {timeout} segundos"
        except httpx.ConnectError:
            result["status_code"] = "connection_error"
            result["error"] = "Error de conexión"
        except Exception as e:
            result["status_code"] = "error"
            result["error"] = str(e)
        
        return result
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrae el título de la página"""
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        return ""
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extrae la meta descripción"""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()
        return ""
    
    def _extract_h1(self, soup: BeautifulSoup) -> str:
        """Extrae el primer H1"""
        h1_tag = soup.find("h1")
        if h1_tag:
            return h1_tag.get_text(strip=True)
        return ""
    
    def _extract_h2_list(self, soup: BeautifulSoup) -> List[str]:
        """Extrae todos los H2"""
        return [tag.get_text(strip=True) for tag in soup.find_all("h2")]
    
    def _extract_h3_list(self, soup: BeautifulSoup) -> List[str]:
        """Extrae todos los H3"""
        return [tag.get_text(strip=True) for tag in soup.find_all("h3")]
    
    def _extract_canonical(self, soup: BeautifulSoup) -> str:
        """Extrae la URL canónica"""
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if canonical and canonical.get("href"):
            return canonical["href"]
        return ""
    
    def _extract_og_title(self, soup: BeautifulSoup) -> str:
        """Extrae el Open Graph title"""
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        return ""
    
    def _extract_og_description(self, soup: BeautifulSoup) -> str:
        """Extrae el Open Graph description"""
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()
        return ""
    
    def validate_urls(self, urls: List[str]) -> tuple[List[str], List[str]]:
        """
        Valida una lista de URLs
        
        Args:
            urls: Lista de URLs a validar
            
        Returns:
            Tupla con (urls_válidas, urls_inválidas)
        """
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            # Añadir protocolo si no lo tiene
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            # Validación básica
            if self._is_valid_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        return valid_urls, invalid_urls
    
    def _is_valid_url(self, url: str) -> bool:
        """Valida si una URL tiene formato correcto"""
        try:
            # Intenta parsear la URL
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
