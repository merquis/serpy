# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time
from datetime import datetime

def render_scraping_booking():
    st.header("Scraping Booking – Bright Data API (por URL directa)")

    st.markdown("Ejecutando scraping para una única URL específica de hotel (Vincci La Plantación del Sur)")
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

        check_in_str = check_in.strftime("%Y-%m-%dT00:00:00.000Z")
        check_out_str = check_out.strftime("%Y-%m-%dT00:00:00.000Z")

        data = [
            {
                "url": "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
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
