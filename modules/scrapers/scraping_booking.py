# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
from modules.utils.drive_utils import subir_json_a_drive

def obtener_datos_booking(urls):
    token = st.secrets["brightdata"]["token"]
    api_url = "https://api.brightdata.com/request"
    resultados_json = []

    for url in urls:
        st.write(f"📡 Scrapeando URL: {url}")
        payload = {
            "zone": "serppy",
            "url": url,
            "format": "raw"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload), timeout=30)
            st.write(f"🔎 Código de respuesta HTTP: {response.status_code}")

            if not response.ok:
                st.error(f"❌ Error {response.status_code} para URL {url}: {response.text}")
                continue

            # Mostrar una pequeña parte del HTML descargado
            st.code(response.text[:500], language="html")

            soup = BeautifulSoup(response.text, "html.parser")

            if soup.title:
                st.write(f"📄 Título de la página: {soup.title.string}")
            else:
                st.warning("⚠️ No hay <title> en el HTML recibido.")

            if soup.body:
                st.write("✅ El body del HTML existe.")
            else:
                st.warning("⚠️ No hay body en el HTML recibido.")

            # 🔥 Buscar nombre de hotel con selectores modernos
            nombre_hotel = soup.select_one('[data-testid="title"]')
            if not nombre_hotel:
                nombre_hotel = soup.select_one('h2.pp-header__title')

            if nombre_hotel:
                st.success(f"🏨 Nombre hotel encontrado: {nombre_hotel.text.strip()}")
            else:
                st.warning(f"⚠️ No se pudo encontrar el nombre del hotel.")

            # 🔎 Otros campos (todavía con los antiguos, los adaptaremos después si quieres)
            valoracion = soup.find("div", class_="b5cd09854e d10a6220b4")
            direccion = soup.find("span", class_="hp_address_subtitle")
            numero_opiniones = soup.find("div", class_="d8eab2cf7f c90c0a70d3 db63693c62")
            precio = soup.find("div", class_="fcab3ed991 bd73d13072")

            st.write(f"⭐ Valoración: {valoracion.text.strip() if valoracion else 'NO ENCONTRADO'}")
            st.write(f"📍 Dirección: {direccion.text.strip() if direccion else 'NO ENCONTRADO'}")
            st.write(f"💬 Opiniones: {numero_opiniones.text.strip() if numero_opiniones else 'NO ENCONTRADO'}")
            st.write(f"💸 Precio: {precio.text.strip() if precio else 'NO ENCONTRADO'}")

            resultados_json.append({
                "url": url,
                "nombre_hotel": nombre_hotel.text.strip() if nombre_hotel else None,
                "valoracion": valoracion.text.strip() if valoracion else None,
                "direccion": direccion.text.strip() if direccion else None,
                "numero_opiniones": numero_opiniones.text.strip() if numero_opiniones else None,
                "precio": precio.text.strip() if precio else None
            })

        except Exception as e:
            st.error(f"❌ Error inesperado: {e}")

    return resultados_json

def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping múltiple de hoteles en Booking")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    col1, _ = st.columns([1, 3])
    with col1:
        buscar_btn = st.button("🔍 Scrapear hoteles")

    st.session_state.urls_input = st.text_area(
        "📝 Pega varias URLs de hoteles de Booking (una por línea)",
        st.session_state.urls_input,
        height=150
    )

    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Consultando BrightData para hoteles Booking..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados
        st.experimental_rerun()

    if st.session_state.resultados_json:
        col1, col2 = st.columns([1, 1])
        with col1:
            nombre_archivo = "datos_hoteles_booking.json"
            json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button("⬇️ Exportar JSON", data=json_bytes, file_name=nombre_archivo, mime="application/json")
        with col2:
            if st.button("☁️ Subir a Google Drive") and st.session_state.get("proyecto_id"):
                enlace = subir_json_a_drive(nombre_archivo, json_bytes, st.session_state.proyecto_id)
                if enlace:
                    st.success(f"✅ Subido correctamente: [Ver archivo]({enlace})", icon="📁")

        st.subheader("📦 Resultado en JSON")
        st.json(st.session_state.resultados_json)
