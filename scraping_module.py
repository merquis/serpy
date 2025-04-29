"""scraping_module.py – Google Search vía ScrapingAnt JSON API (free)."""
from __future__ import annotations
import subprocess, sys, streamlit as st, requests
from urllib.parse import quote_plus
from typing import List, Tuple

# BeautifulSoup sigue por si algún día parseas HTML crudo
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4"])
        from bs4 import BeautifulSoup
    except Exception:
        BeautifulSoup = None

TOKEN       = st.secrets.get("scrapingant", {}).get("token", "")
MAX_RESULTS = 10
TIMEOUT     = 15

# ───────────────────────── Fetch vía JSON endpoint ────────────────────────
def fetch_results(query: str) -> Tuple[List[str] | None, str | None]:
    if not TOKEN:
        return None, "Falta el token de ScrapingAnt en secrets."

    api_url = "https://api.scrapingant.com/v1/google"
    params  = {
        "query": quote_plus(query),
        "gl":    "es",   # geolocalización España
        "hl":    "es",   # idioma español
        "x-api-key": TOKEN,
    }

    try:
        r = requests.get(api_url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        links = [item["link"] for item in data.get("organic", [])][:MAX_RESULTS]
        return links, None
    except requests.RequestException as e:
        return None, f"Error ScrapingAnt: {e}"
    except (ValueError, KeyError):
        return None, "Formato JSON inesperado en la respuesta."

# ───────────────────────────── Streamlit UI ───────────────────────────────
def render() -> None:
    st.title("🔎 Scraping Google (ScrapingAnt JSON API)")

    q = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and q.strip():
        with st.spinner("Consultando Google…"):
            urls, err = fetch_results(q.strip())

        if err:
            st.error(err)
            return

        if not urls:
            st.warning("No se devolvieron resultados.")
            return

        st.success(f"Top {len(urls)} resultados")
        for i, u in enumerate(urls, 1):
            st.markdown(f"{i}. [{u}]({u})")

        st.download_button(
            "⬇️ Descargar CSV",
            data="\n".join(urls).encode(),
            file_name=f"google_{quote_plus(q)[:30]}.csv",
            mime="text/csv",
        )
