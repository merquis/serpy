import streamlit as st
import requests

def google_search(query):
    api_key = st.secrets["scrapingant"]["token"]
    url = "https://api.scrapingant.com/v2/general"
    params = {
        "url": f"https://www.google.es/search?q={query.replace(' ', '+')}",
        "x-api-key": api_key
    }
    response = requests.get(url, params=params, timeout=15)
    return response.text

def extract_google_urls(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a"):
        href = a.get("href")
        if href and "/url?q=" in href:
            clean = href.split("/url?q=")[1].split("&")[0]
            if "google.com" not in clean and not clean.startswith("/"):
                links.append(clean)
    return links[:10]

def render():
    st.title("🕸️ Scraping de Google (ScrapingAnt)")
    query = st.text_input("Frase de búsqueda")

    if st.button("Buscar") and query:
        with st.spinner("Consultando a Google..."):
            html = google_search(query)
            urls = extract_google_urls(html)

        if urls:
            st.success("Resultados encontrados:")
            for i, link in enumerate(urls, 1):
                st.markdown(f"{i}. [{link}]({link})")
        else:
            st.warning("No se encontraron resultados.")
