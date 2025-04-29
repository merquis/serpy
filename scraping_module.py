import streamlit as st
import http.client
from urllib.parse import quote_plus

def render():
    st.title("🔎 Scraping Google España (ScrapingAnt API)")

    query = st.text_input("Frase de búsqueda")
    if st.button("Buscar") and query.strip():
        with st.spinner("Conectando con la API de ScrapingAnt…"):
            result, error = consultar_api_scrapingant(query.strip())

        if error:
            st.error(error)
        else:
            st.success("Respuesta recibida:")
            st.code(result)

def consultar_api_scrapingant(query: str):
    token = "7970f04a3cff4b9d89a4a287c2cd1ba2"
    buscador = f"https://www.google.es/search?q={quote_plus(query)}"

    ruta = f"/v2/general?url={quote_plus(buscador)}&x-api-key={token}"

    try:
        conn = http.client.HTTPSConnection("api.scrapingant.com", timeout=20)
        conn.request("GET", ruta)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()

        if res.status != 200:
            return None, f"❌ Error {res.status} {res.reason}:\n{data}"
        return data, None

    except Exception as e:
        return None, f"⚠️ Excepción al conectar: {e}"
