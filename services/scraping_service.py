
"""Servicio para scraping de resultados de Google mediante BrightData"""
import requests
import urllib.parse
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from config import config
import logging

logger = logging.getLogger(__name__)

class GoogleScrapingService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or config.brightdata_token
        self.api_url = "https://api.brightdata.com/request"

    def search_multiple_queries(
        self,
        queries: List[str],
        num_results: int = 10,
        language_code: str = "es",
        region_code: str = "es",
        google_domain: str = "google.es"
    ) -> List[Dict[str, Any]]:
        results = []
        for query in queries:
            try:
                result = self._search_single_query(query, num_results, language_code, region_code, google_domain)
                results.append(result)
            except Exception as e:
                logger.error(f"Error en búsqueda '{query}': {e}")
                results.append({
                    "busqueda": query,
                    "error": str(e),
                    "urls": []
                })
        return results

    def _search_single_query(self, query, num_results, language_code, region_code, google_domain):
        urls = []
        encoded_query = urllib.parse.quote(query)
        for start in range(0, num_results, config.scraping.step_size):
            search_url = self._build_search_url(encoded_query, language_code, region_code, google_domain, start)
            try:
                html_content = self._fetch_page(search_url)
                page_urls = self._extract_urls(html_content)
                urls.extend(page_urls)
                if len(urls) >= num_results:
                    break
            except Exception as e:
                logger.error(f"Error fetching page {start} for '{query}': {e}")
                break

        unique_urls = list(dict.fromkeys(urls[:num_results]))
        return {
            "busqueda": query,
            "idioma": language_code,
            "region": region_code,
            "dominio": google_domain,
            "url_busqueda": search_url,
            "urls": unique_urls
        }

    def _build_search_url(self, query, hl, gl, domain, start):
        return f"https://{domain}/search?q={query}&hl={hl}&gl={gl}&start={start}"

    def _fetch_page(self, url):
        payload = {
            "zone": "serppy",
            "url": url,
            "format": "raw"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=config.scraping.timeout)
        response.raise_for_status()
        return response.text

    def _extract_urls(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        for link in soup.select("a:has(h3)"):
            href = link.get("href")
            if href and href.startswith("http"):
                urls.append(href)
        return urls
