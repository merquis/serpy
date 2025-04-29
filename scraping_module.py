"""scraping_module.py
Scraping productos de eBay usando ScrapingAnt y BeautifulSoup.
"""

import http.client
from bs4 import BeautifulSoup
import streamlit as st

# Token API de ScrapingAnt directo
API_KEY = "7970f04a3cff4b9d89a4a287c2cd1ba2"

# ────────── Funciones API ──────────
def fetch_ebay_html(query: str) -> BeautifulSoup | None:
    encoded_query = query.replace(" ", "+")
    path = f"/v2/general?url=https://www.ebay.com/sch/i.html?_nkw={encoded_query}&x-api-key={API_KEY}"
    try:
        conn = http.client.HTTPSConnection("api.scrapingant.com", timeout=15)
        conn.request("GET", path)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return BeautifulSoup(data, 'html.parser')
    except Exception as e:
        st.error(f"Error al conectar con ScrapingAnt: {e}")
        return None

# ────────── UI STREAMLIT ──────────
def render():
    st.title("🔎 Scraping eBay (ScrapingAnt)")

    query = st.text_input("Buscar producto en eBay", value="MacBook")
    if st.button("Buscar") and query.strip():
        with st.spinner("Consultando eBay..."):
            soup = fetch_ebay_html(query.strip())

        if not soup:
            return

        titles = soup.find_all('div', class_='s-item__title')
        prices = soup.find_all('span', class_='s-item__price')

        resultados = list(zip(titles[2:], prices[2:]))

        if not resultados:
            st.warning("No se encontraron resultados.")
            return

        st.success(f"Resultados para '{query}':")
        for i, (t, p) in enumerate(resultados, 1):
            st.markdown(f"{i}. **{t.text}** → {p.text}")

        st.download_button(
            "⬇️ Descargar CSV",
            data="\n".join([f"{t.text},{p.text}" for t, p in resultados]).encode(),
            file_name=f"ebay_{query[:30]}.csv",
            mime="text/csv",
        )
