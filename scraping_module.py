"""scraping_module.py
Scraping de los 10 primeros resultados orgánicos de Google España usando ScrapingAnt.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Tuple

import streamlit as st
import requests
from urllib.parse import quote_plus

# ───────────────────────────────── CONFIG ────────────────────────────────── #

@dataclass
class Config:
    scrapingant_token: str | None = st.secrets.get("scrapingant", {}).get("token")
    google_domain: str = "https://www.google.es/search?q="
    max_results: int = 10
    timeout: int = 20  # seg

CFG = Config()

# ─────────────────────────── DEPENDENCIA BeautifulSoup ───────────────────── #

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError as e:  # pragma: no cover
    st.error(
        "❌ Falta la dependencia *beautifulsoup4*.\n\n"
        "Añádela a `requirements.txt` y haz **Clear cache & Redeploy**.\n\n"
        f"Detalle técnico: {e}"
    )
    st.stop()

# ────────────────────────────── CORE FUNCTIONS ───────────────────────────── #

def build_scrapingant_url(query: str, token: str) -> str:
    """Construye la URL completa para ScrapingAnt."""
    search_url = f"{CFG.google_domain}{quote_plus(query)}"
    api = "https://api.scrapingant.com/v2/general"
    return f"{api}?url={quote_plus(search_url)}&x-api-key={token}"

def fetch_google_html(query: str) -> Tuple[str | None, str | None]:
    """
    Devuelve (html, error); si error ≠ None, html será None.
    Maneja timeouts y errores HTTP.
    """
    if not CFG.scrapingant_token:  # token perdido
        return None, "No se encontró el token de ScrapingAnt en st.secrets."

    url = build_scrapingant_url(query, CFG.scrapingant_token)
    try:
        r = requests.get(url, timeout=CFG.timeout)
        r.raise_for_status()
        return r.text, None
    except requests.RequestException as exc:
        return None, f"Fallo de petición a ScrapingAnt: {exc}"

def parse_google_urls(html: str, max_results: int = 10) -> List[str]:
    """Extrae URLs orgánicas de la página de resultados de Google."""
    soup = BeautifulSoup(html, "html.parser")
    urls: List[str] = []
    pattern = re.compile(r"^/url\?q=(https?://[^&]+)&")

    for a in soup.select("a"):
        href = a.get("href", "")
        match = pattern.match(href)
        if match:
            url = match.group(1)
            # Excluir dominios de Google y duplicados
            if "google." not in url and url not in urls:
                urls.append(url)
        if len(urls) >= max_results:
            break
    return urls

# ───────────────────────────── STREAMLIT UI ─────────────────────────────── #

def render() -> None:
    st.title("🔎 Scraping de Google (via ScrapingAnt)")

    query = st.text_input("Frase de búsqueda en Google España")
    if st.button("Buscar") and query.strip():
        with st.spinner("Obteniendo resultados…"):
            html, err = fetch_google_html(query.strip())

        if err:
            st.error(err)
            return

        urls = parse_google_urls(html, CFG.max_results)

        if not urls:
            st.warning("No se encontraron URLs orgánicas (o Google cambió el layout).")
            return

        st.success(f"Top {len(urls)} resultados para «{query}»")
        for i, link in enumerate(urls, 1):
            st.markdown(f"{i}. [{link}]({link})")

        # Descarga opcional como CSV
        csv = "\n".join(urls).encode("utf-8")
        st.download_button(
            "⬇️ Descargar CSV",
            data=csv,
            file_name=f"google_results_{quote_plus(query)[:30]}.csv",
            mime="text/csv",
        )
