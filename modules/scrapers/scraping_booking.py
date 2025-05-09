# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time
from datetime import datetime

def render_scraping_booking():
    st.header("Scraping Booking – Bright Data API (por ciudad y fechas)")

    with st.form("booking_form"):
        st.markdown("Introduce los parámetros de búsqueda:")
        ciudad_1 = st.text_input("📍 Ciudad 1", "New York")
        ciudad_2 = st.text_input("📍 Ciudad 2", "Paris")
        check_in = st.date_input("📅 Fecha de entrada", datetime(2025, 2, 1))
        check_out = st.date_input("📅 Fecha de salida", datetime(2025, 2, 10))
        adultos = st.number_input("👥 Adultos", min_value=1, value=2)
        ninos = st.number_input("🧒 Niños", min_value=0, value=1)
        habitaciones = st.number_input("🛏️ Habitaciones", min_value=1, value=1)
        enviar = st.form_submit_button("🔍 Buscar hoteles")

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

        check_in_str = check_in.strftime("%Y-%m-%dT00:00:00.000Z")
        check_out_str = check_out.strftime("%Y-%m-%dT00:00:00.000Z")

        data = [
            {
                "url": "https://www.booking.com",
                "location": ciudad_1,
                "check_in": check_in_str,
                "check_out": check_out_str,
                "adults": adultos,
                "children": ninos,
                "rooms": habitaciones,
                "country": "US",
                "currency": ""
            },
            {
                "url": "https://www.booking.com",
                "location": ciudad_2,
                "check_in": check_in_str,
                "check_out": check_out_str,
                "adults": adultos,
                "rooms": habitaciones,
                "country": "FR",
                "currency": ""
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

        result_url = f"https://api.brightdata.com/datasets/v3/data?dataset_id={params['dataset_id']}&snapshot_id={snapshot_id}&limit=10"
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
            st.subheader("🏨 Hoteles encontrados:")
            for i, hotel in enumerate(results):
                nombre = hotel.get("title", "Sin nombre")
                direccion = hotel.get("address") or hotel.get("location") or "Sin dirección"
                puntuacion = hotel.get("review_score", "Sin puntuación")
                st.markdown(f"### {i+1}. {nombre}")
                st.write(f"📍 {direccion}")
                st.write(f"⭐ {puntuacion}")
                imagenes = hotel.get("images")
                if imagenes and isinstance(imagenes, list):
                    st.image(imagenes[0], width=300)
                st.markdown("---")
        else:
            st.warning("No se devolvieron resultados aún.")
