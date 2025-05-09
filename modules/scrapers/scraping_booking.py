# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time
from datetime import datetime

def render_scraping_booking():
    st.header("Scraping Booking – Bright Data API")

    with st.form("booking_form"):
        location = st.text_input("📍 Ciudad destino", "Paris")
        check_in = st.date_input("📅 Fecha de entrada", datetime(2025, 4, 30))
        check_out = st.date_input("📅 Fecha de salida", datetime(2025, 5, 7))
        adults = st.number_input("👥 Número de adultos", min_value=1, value=2)
        rooms = st.number_input("🛏️ Habitaciones", min_value=1, value=1)
        country = st.text_input("🌍 Código de país (FR, ES, IT...)", "FR")
        submit = st.form_submit_button("🔍 Buscar alojamiento")

    if submit:
        st.info("⏳ Solicitando scraping a Bright Data...")
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
                "url": "https://www.booking.com",
                "location": location,
                "check_in": check_in.strftime("%Y-%m-%dT00:00:00.000Z"),
                "check_out": check_out.strftime("%Y-%m-%dT00:00:00.000Z"),
                "adults": adults,
                "rooms": rooms,
                "country": country,
                "currency": ""
            }
        ]

        response = requests.post(url, headers=headers, params=params, json=data)
        job = response.json()

        if "snapshot_id" in job:
            st.success(f"✅ Snapshot generado: {job['snapshot_id']}")
            time.sleep(6)
        else:
            st.error(f"❌ Error lanzando scraping: {job}")
            return

        # st.success(f"✅ Scraping lanzado. Job ID: {job['job_id']}")  # Eliminado porque solo usamos snapshot_id
        time.sleep(6)

        result_url = f"https://api.brightdata.com/datasets/v3/data?dataset_id={params['dataset_id']}&snapshot_id={job['snapshot_id']}&limit=1"
        result_resp = requests.get(result_url, headers=headers)
        results = result_resp.json()

        if results and isinstance(results, list):
            hotel = results[0]
            nombre = hotel.get("title")
            if nombre:
                st.success(f"🏨 Nombre del primer hotel: {nombre}")
            else:
                st.warning("No se encontró el nombre del hotel en el campo 'title'.")
        else:
            st.warning("No se devolvieron resultados aún.")
