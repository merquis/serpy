"""scraping_module.py
Scraping de resultados orgánicos de Bing usando ScrapingAnt API con http.client.
"""

from __future__ import annotations
import http.client
import re
from urllib.parse import quote_plus
from typing import List, Tuple

import streamlit as st
from bs4 import BeautifulSoup

# ────────── CONFIGURACIÓN ──────────
TOKEN       = "7970f04a3cff4b9d89a4a287c2cd1ba2"
API_HOST    = "api.scrapingant.com"
API_PATH    = "/v2/general"
MAX_RESULTS = 10
URL_RE      = re.compile(r"^https?://")

# ────────── CORE ──────────
def fetch_html_bing(query: str) -> Tuple[str | None, str | None]:
    """
    Lanza la petición a ScrapingAnt con una búsqueda en Bing.
    Devuelve (html, error). Si hay error, html será None.
    """
    bing_url = f"https://www.bing.com/search?q={quote_plus(query)}"
    path = f"{API_PATH}?url={quote_plus(bing_url)}&x-api-key={TOKEN}"

    try:
        conn = http.client.HTTPSConnection(API_HOST, timeout=20)
        conn.request("GET", path)
        res = conn.getresponse()
        text = res.read().decode("utf-8")
        conn.close()
    except Exception as e:
        return None, f"Error de conexión: {e}"

    if res.status != 200:
        try:
            import json
            detail = json.loads(text).get("detail", "")
        except Exception:
            detail = ""
        return None, f"{res.status} {res.reason}. {detail}"

    return text, None

def parse_urls_bing(html: str) -> List[str]:
    """Extrae hasta MAX_RESULTS URLs de los resultados de Bing."""
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.select("li.b_algo h2 a"):
        href = a.get("href", "")
        if href and URL_RE.match(href):
            links.append(href)
        if len(links) >= MAX_RESULTS:
            break
    return links

# ────────── UI STREAMLIT ──────────
def render() -> None:
    st.title("🔎 Scraping Bing (ScrapingAnt API)")

    query = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and query.strip():
        with st.spinner("Buscando en Bing..."):
            html, err = fetch_html_bing(query.strip())

        if err:
            st.error(f"❌ {err}")
            return

        urls = parse_urls_bing(html)
        if not urls:
            st.warning("No se encontraron URLs.")
            return

        st.success(f"Top {len(urls)} resultados encontrados:")
        for i, link in enumerate(urls, 1):
            st.markdown(f"{i}. [{link}]({link})")

        st.download_button(
            "⬇️ Descargar CSV",
            data="\n".join(urls).encode(),
            file_name=f"bing_{quote_plus(query)[:30]}.csv",
            mime="text/csv",
        )
