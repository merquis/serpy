# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time
from datetime import datetime

def render_scraping_booking():
    st.header("Scraping Booking – Bright Data API (por URL directa)")

    url_input = st.text_input("🔗 URL del hotel en Booking", "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html")
    enviar = st.button("🔍 Obtener hotel")

    if enviar:
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {st.secrets['brightdata_booking']['token']}",
            "Content-Type": "application/json"
        }
        params = {
            "dataset_id": "gd_m4bf7a917zfezv9d5",
            "include_errors": "true"
        }

        
        data = [
            {
                "url": url_input.strip(),
                "location": "Tenerife",
                "check_in": "2025-06-01T00:00:00.000Z",
                "check_out": "2025-06-02T00:00:00.000Z",
                "adults": 2,
                "rooms": 1,
                "country": "ES",
                "currency": "EUR"
            }
        ]

        st.info("⏳ Enviando solicitud a Bright Data...")
        response = requests.post(url, headers=headers, params=params, json=data)
        job = response.json()

        if "snapshot_id" in job:
            snapshot_id = job["snapshot_id"]
            st.success(f"✅ Snapshot generado: {snapshot_id}")
            time.sleep(6)
        else:
            st.error(f"❌ Error lanzando scraping: {job}")
            return

        result_url = f"https://api.brightdata.com/datasets/v2/snapshot/{snapshot_id}/data?limit=10"
        result_resp = requests.get(result_url, headers=headers)

        if result_resp.status_code == 200:
            try:
                results = result_resp.json()
            except Exception as e:
                st.error(f"❌ Error al parsear JSON: {e}")
                st.text(result_resp.text[:1000])
                return
        else:
            st.error(f"❌ Error en respuesta HTTP: {result_resp.status_code}")
            st.text(result_resp.text[:1000])
            return

        if results and isinstance(results, list):
            nombre = results[0].get("title", "Sin nombre")
            st.success(f"🏨 Nombre del hotel: {nombre}")
        else:
            st.warning("No se devolvieron resultados aún.")
