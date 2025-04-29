"""scraping_module.py
Top-10 resultados orgánicos de Bing usando ScrapingAnt (HTTP/1.1 via http.client).
"""

from __future__ import annotations
import http.client
import re
from urllib.parse import quote_plus
from typing import List, Tuple

import streamlit as st
from bs4 import BeautifulSoup  # requieres beautifulsoup4 en requirements

# ─────────────────── CONFIG ────────────────────
TOKEN       = st.secrets.get("scrapingant", {}).get("token", "")
API_HOST    = "api.scrapingant.com"
API_PATH    = "/v2/general"
MAX_RESULTS = 10
URL_RE      = re.compile(r"^https?://")

# ─────────────────── CORE ──────────────────────
def fetch_html(query: str) -> Tuple[str | None, str | None]:
    """
    Lanza la petición HTTP/1.1 usando http.client.
    Devuelve (html, error). Si error≠None, html será None.
    """
    if not TOKEN:
        return None, "Falta el token de ScrapingAnt en st.secrets."

    # Nuestra URL de búsqueda en Bing
    bing_url = f"https://www.bing.com/search?q={quote_plus(query)}"

    # Montamos la ruta con parámetros ya codificados
    path = (
        f"{API_PATH}"
        f"?url={quote_plus(bing_url)}"
        f"&x-api-key={TOKEN}"
    )

    try:
        conn = http.client.HTTPSConnection(API_HOST, timeout=20)
        conn.request("GET", path)
        res = conn.getresponse()
        text = res.read().decode("utf-8")
        conn.close()
    except Exception as e:
        return None, f"Error al conectar con ScrapingAnt: {e}"

    if res.status != 200:
        # extraemos detalle si viene en JSON
        detail = ""
        try:
            import json
            detail = json.loads(text).get("detail", "")
        except Exception:
            pass
        return None, f"{res.status} {res.reason}. {detail}"

    return text, None

def parse_urls(html: str) -> List[str]:
    """Extrae los primeros MAX_RESULTS enlaces de los resultados de Bing."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("li.b_algo h2 a"):
        href = a.get("href", "")
        if href and URL_RE.match(href):
            links.append(href)
        if len(links) >= MAX_RESULTS:
            break
    return links

# ─────────────────── STREAMLIT UI ─────────────────────
def render() -> None:
    st.title("🔎 Scraping Bing (ScrapingAnt via http.client)")

    query = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and query.strip():
        with st.spinner("Consultando Bing…"):
            html, err = fetch_html(query.strip())

        if err:
            st.error(err)
            return

        urls = parse_urls(html)
        if not urls:
            st.warning("No se extrajeron URLs.")
            return

        st.success(f"Top {len(urls)} resultados")
        for i, link in enumerate(urls, 1):
            st.markdown(f"{i}. [{link}]({link})")

        st.download_button(
            "⬇️ Descargar CSV",
            data="\n".join(urls).encode(),
            file_name=f"bing_{quote_plus(query)[:30]}.csv",
            mime="text/csv",
        )
