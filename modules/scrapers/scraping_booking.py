# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time

def render_scraping_booking():
    st.header("Scraping Booking por URL directa – Bright Data API")

    if st.button("🔍 Scrapear 2 hoteles desde Bright Data"):
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {st.secrets['brightdata_booking']['token']}",
            "Content-Type": "application/json",
        }
        params = {
            "dataset_id": "gd_m5mbdl081229ln6t4a",
            "include_errors": "true",
        }
        data = [
            {"url": "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"},
            {"url": "https://www.booking.com/hotel/es/jardines-de-nivaria.es.html"},
        ]

        st.info("⏳ Enviando solicitud a Bright Data...")
        response = requests.post(url, headers=headers, params=params, json=data)
        result = response.json()

        if "snapshot_id" in result:
            snapshot_id = result["snapshot_id"]
            st.success(f"✅ Snapshot generado: {snapshot_id}")
            time.sleep(6)

            result_url = f"https://api.brightdata.com/datasets/v3/data?dataset_id={params['dataset_id']}&snapshot_id={snapshot_id}&limit=10"
            res = requests.get(result_url, headers=headers)

            if res.status_code == 200:
                try:
                    hoteles = res.json()
                    st.subheader("🏨 Hoteles encontrados:")
                    for hotel in hoteles:
                        titulo = hotel.get("title", "Nombre no disponible")
                        st.markdown(f"- {titulo}")
                except Exception as e:
                    st.error(f"❌ Error al procesar respuesta JSON: {e}")
                    st.code(res.text[:1000])
            else:
                st.error(f"❌ Error en respuesta HTTP: {res.status_code}")
                st.code(res.text[:1000])
        else:
            st.error("❌ No se generó un snapshot. Revisa los parámetros o el dataset_id.")
            st.code(result)
