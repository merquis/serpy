"""scraping_module.py
Top-10 resultados orgánicos de Bing usando ScrapingAnt (plan Free) vía http.client.
Lectura segura de token desde st.secrets.
"""

from __future__ import annotations
import http.client
import re
import json
from urllib.parse import quote_plus
from typing import List, Tuple

import streamlit as st
from bs4 import BeautifulSoup

# ─────────────────── Configuración ─────────────────────────────
TOKEN       = st.secrets["scrapingant"]["token"]
API_HOST    = "api.scrapingant.com"
API_PATH    = "/v2/general"
MAX_RESULTS = 10
URL_RE      = re.compile(r"^https?://")

# ─────────────────── Funciones Core ─────────────────────────────
def fetch_html(query: str) -> Tuple[str | None, str | None]:
    """Realiza la petición a ScrapingAnt. Devuelve (html, error)."""
    if not TOKEN:
        return None, "Token de ScrapingAnt no configurado en secrets."

    search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
    api_request = f"{API_PATH}?url={quote_plus(search_url)}&x-api-key={TOKEN}"

    try:
        conn = http.client.HTTPSConnection(API_HOST, timeout=20)
        conn.request("GET", api_request)
        res = conn.getresponse()
        text = res.read().decode("utf-8")
        conn.close()
    except Exception as e:
        return None, f"Error de conexión con ScrapingAnt: {e}"

    if res.status != 200:
        try:
            detail = json.loads(text).get("detail", "")
        except Exception:
            detail = ""
        return None, f"{res.status} {res.reason}. {detail}"

    return text, None

def parse_urls(html: str) -> List[str]:
    """Extrae enlaces de resultados de Bing."""
    soup = BeautifulSoup(html, "html.parser")
    links = [
        a["href"] for a in soup.select("li.b_algo h2 a")
        if a.has_attr("href") and URL_RE.match(a["href"])
    ]
    return links[:MAX_RESULTS]

# ─────────────────── Streamlit UI ───────────────────────────────
def render() -> None:
    st.title("🔎 Scraping Bing (ScrapingAnt • Profesional)")

    query = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and query.strip():
        with st.spinner("Consultando Bing…"):
            html, error = fetch_html(query.strip())

        if error:
            st.error(error)
            return

        urls = parse_urls(html)
        if not urls:
            st.warning("No se extrajeron URLs.")
            return

        st.success(f"Top {len(urls)} resultados encontrados")
        for idx, url in enumerate(urls, 1):
            st.markdown(f"{idx}. [{url}]({url})")

        st.download_button(
            "⬇️ Descargar CSV",
            data="\n".join(urls).encode(),
            file_name=f"bing_{quote_plus(query)[:30]}.csv",
            mime="text/csv",
        )
