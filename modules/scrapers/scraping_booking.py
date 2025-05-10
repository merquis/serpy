import streamlit as st
import requests
from bs4 import BeautifulSoup

def obtener_nombre_hotel(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        nombre_hotel = soup.find("h2", class_="d2fee87262 pp-header__title")
        if nombre_hotel:
            return nombre_hotel.text.strip()
        else:
            return "⚠️ No se encontró el nombre del hotel."
    except Exception as e:
        return f"❌ Error: {e}"

# ───────────────────────────────────────────────────────────────
# INTERFAZ DE USUARIO
# ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Scraper de Booking", page_icon="🏨")
st.title("🏨 Scraper sencillo de nombre de hotel (Booking.com)")

url = st.text_input("🔗 Introduce la URL del hotel en Booking.com:")

if st.button("Extraer nombre del hotel"):
    if url:
        with st.spinner("🔎 Extrayendo información..."):
            nombre = obtener_nombre_hotel(url)
        st.success(f"✅ Nombre del hotel: **{nombre}**")
    else:
        st.warning("⚠️ Por favor, introduce una URL válida.")
