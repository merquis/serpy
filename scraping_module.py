"""scraping_module.py
Top-10 resultados orgánicos de Bing usando ScrapingAnt (plan Free).
No depende de `scrapingant-client`, solo de `requests`.
"""

from __future__ import annotations
from urllib.parse import quote_plus
from typing import List, Tuple
import re

import streamlit as st
import requests
from bs4 import BeautifulSoup  # ya está en requirements

TOKEN        = st.secrets.get("scrapingant", {}).get("token", "")
API_URL      = "https://api.scrapingant.com/v2/general"
MAX_RESULTS  = 10
TIMEOUT      = 20
URL_RE       = re.compile(r"^https?://")

def fetch_html(query: str) -> Tuple[str | None, str | None]:
    """Devuelve (html, error).  Si error ≠ None, html será None."""
    if not TOKEN:
        return None, "Falta el token de ScrapingAnt en secrets."

    bing_url = f"https://www.bing.com/search?q={quote_plus(query)}"

    try:
        r = requests.get(
            API_URL,
            params={"url": bing_url, "x-api-key": TOKEN},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.text, None
    except requests.RequestException as e:
        return None, f"Error ScrapingAnt: {e}"

def parse_urls(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        a["href"]
        for a in soup.select("li.b_algo h2 a")[:MAX_RESULTS]
        if a.has_attr("href") and URL_RE.match(a["href"])
    ]

# ───────────────────── Streamlit UI ─────────────────────
def render() -> None:
    st.title("🔎 Scraping Bing (ScrapingAnt – plan Free)")

    q = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and q.strip():
        with st.spinner("Consultando Bing…"):
            html, err = fetch_html(q.strip())

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
            file_name=f"bing_{quote_plus(q)[:30]}.csv",
            mime="text/csv",
        )
