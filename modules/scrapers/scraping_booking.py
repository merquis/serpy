# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
from bs4 import BeautifulSoup

def render_scraping_booking():
    st.header("Scraping Booking (via Bright Data API)")
    st.markdown("Extraer nombre del hotel desde una URL de Booking usando Bright Data")

    url = st.text_input("URL del hotel en Booking", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")

    if st.button("🔍 Obtener nombre del hotel via Bright Data"):
        try:
            api_key = st.secrets["brightdata"]["token"]  # Guardar en .streamlit/secrets.toml
            dataset_id = "hl_bdec3e3e"  # Tu dataset ID real
            endpoint = "https://api.brightdata.com/datasets/v3/trigger"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            params = {
                "dataset_id": dataset_id,
                "include_errors": "true"
            }

            data = [ {"url": url} ]

            st.info("⏳ Solicitando scraping a Bright Data...")
            response = requests.post(endpoint, headers=headers, params=params, json=data)
            job_info = response.json()

            if "job_id" not in job_info:
                st.error("❌ No se pudo iniciar el scraping. Revisa el dataset_id o la URL.")
                return

            job_id = job_info["job_id"]
            st.success(f"✅ Scraping lanzado. Job ID: {job_id}")

            # Obtener resultados
            st.info("⏳ Esperando y recuperando resultados...")
            import time
            time.sleep(5)  # Pequeña espera antes de recuperar

            result_endpoint = f"https://api.brightdata.com/datasets/v3/data?dataset_id={dataset_id}&limit=1"
            result_resp = requests.get(result_endpoint, headers=headers)
            resultados = result_resp.json()

            if resultados and isinstance(resultados, list):
                html = resultados[0].get("_html", "")
                soup = BeautifulSoup(html, "html.parser")
                titulo = soup.find("h2")
                if titulo:
                    nombre = titulo.get_text(strip=True)
                    st.success(f"🏨 Nombre detectado: {nombre}")
                else:
                    st.warning("No se encontró ninguna etiqueta <h2> en la respuesta HTML.")
            else:
                st.warning("No se encontraron resultados válidos todavía. Espera unos segundos y vuelve a intentar.")

        except Exception as e:
            st.error(f"❌ Error al usar la API de Bright Data: {e}")
