"""scraping_module.py
Top-10 resultados orgánicos de **Bing** usando el SDK oficial de ScrapingAnt.
Funciona con el plan Free.
"""

from __future__ import annotations
import re
from urllib.parse import quote_plus
from typing import List, Tuple

import streamlit as st
from scrapingant_client import ScrapingAntClient
from bs4 import BeautifulSoup

# ─────────────────── CONFIG ────────────────────
TOKEN = st.secrets.get("scrapingant", {}).get("token", "")
MAX_RESULTS = 10
TIMEOUT = 20

client = ScrapingAntClient(TOKEN, timeout=TIMEOUT)

PAT_URL = re.compile(r"^https?://")

# ─────────────────── CORE ──────────────────────
def fetch_bing_results(query: str) -> Tuple[List[str] | None, str | None]:
    """Devuelve (urls, error).  Si error ≠ None, urls será None."""
    if not TOKEN:
        return None, "Falta el token de ScrapingAnt en secrets."

    bing_url = f"https://www.bing.com/search?q={quote_plus(query)}"

    try:
        resp = client.general_request(url=bing_url, render_js=False)
        html = resp.text
    except Exception as exc:  # problemas HTTP / red / token
        return None, f"Error ScrapingAnt: {exc}"

    soup = BeautifulSoup(html, "html.parser")
    urls = [
        a["href"]
        for a in soup.select("li.b_algo h2 a")
        if a.has_attr("href") and PAT_URL.match(a["href"])
    ][:MAX_RESULTS]

    return urls, None

# ─────────────────── UI ────────────────────────
def render() -> None:
    st.title("🔎 Scraping Bing (ScrapingAnt • plan gratuito)")

    query = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and query.strip():
        with st.spinner("Consultando Bing…"):
            urls, err = fetch_bing_results(query.strip())

        if err:
            st.error(err)
            return

        if not urls:
            st.warning("No se extrajeron URLs.")
            return

        st.success(f"Top {len(urls)} resultados")
        for i, u in enumerate(urls, 1):
            st.markdown(f"{i}. [{u}]({u})")

        st.download_button(
            "⬇️ Descargar CSV",
            data="\n".join(urls).encode(),
            file_name=f"bing_{quote_plus(query)[:30]}.csv",
            mime="text/csv",
        )
