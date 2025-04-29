"""scraping_module.py – Top-10 URLs orgánicas de Google ES vía ScrapingAnt."""
from __future__ import annotations
import re, subprocess, sys
from urllib.parse import quote_plus
from typing import List, Tuple
import requests, streamlit as st

# ── BeautifulSoup con instalación dinámica (solo la 1.ª vez) ───────────────
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
        from bs4 import BeautifulSoup
    except Exception:
        BeautifulSoup = None   # fallback a regex

# ── Config ────────────────────────────────────────────────────────────────
TOKEN        = st.secrets.get("scrapingant", {}).get("token", "")
GOOGLE       = "https://www.google.es/search?q="
MAX_RESULTS  = 10
TIMEOUT      = 20

# ── Networking ────────────────────────────────────────────────────────────
def fetch_html(query: str) -> Tuple[str | None, str | None]:
    """Devuelve (html, error). Si error != None, html será None."""
    if not TOKEN:
        return None, "Falta el token de ScrapingAnt en secrets."

    search_url = GOOGLE + quote_plus(query)
    api_url    = "https://api.scrapingant.com/v2/general"

    try:
        r = requests.get(
            api_url,
            params={"url": search_url, "x-api-key": TOKEN},  # encoding correcto
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.text, None
    except requests.RequestException as e:
        return None, f"Error ScrapingAnt: {e}"

# ── Parsing ───────────────────────────────────────────────────────────────
def parse_urls(html: str) -> List[str]:
    pattern = re.compile(r"/url\?q=(https?://[^&]+)&")
    urls: List[str] = []

    if BeautifulSoup:                                      # modo normal
        soup = BeautifulSoup(html, "html.parser")
        hrefs = (a.get("href", "") for a in soup.select("a"))
    else:                                                 # fallback regex
        hrefs = pattern.findall(html)

    for href in hrefs:
        match = pattern.match(href) if BeautifulSoup else (href,)
        if match:
            url = match[1] if BeautifulSoup else match[0]
            if "google." not in url and url not in urls:
                urls.append(url)
        if len(urls) >= MAX_RESULTS:
            break
    return urls

# ── Streamlit UI ──────────────────────────────────────────────────────────
def render() -> None:
    st.title("🔎 Scraping Google (ScrapingAnt)")

    query = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and query.strip():
        with st.spinner("Consultando Google…"):
            html, err = fetch_html(query.strip())

        if err:
            st.error(err)
            return

        urls = parse_urls(html)
        if not urls:
            st.warning("No se extrajeron URLs orgánicas.")
            return

        st.success(f"Top {len(urls)} resultados")
        for i, u in enumerate(urls, 1):
            st.markdown(f"{i}. [{u}]({u})")

        st.download_button(
            "⬇️ Descargar CSV",
            data="\n".join(urls).encode(),
            file_name=f"google_{quote_plus(query)[:30]}.csv",
            mime="text/csv",
        )
