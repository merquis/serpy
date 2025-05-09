import streamlit as st
import requests
import time

def render_scraping_booking():
    st.header("📦 Scraping de Hoteles en Booking (Bright Data API)")

    if st.button("🔍 Obtener hoteles desde Bright Data"):
        # API setup
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {st.secrets['brightdata_booking']['token']}",
            "Content-Type": "application/json",
        }
        params = {
            "dataset_id": "gd_m5mbdl081229ln6t4a",
            "include_errors": "true",
        }

        # URLs de los hoteles (scraping directo)
        data = [
            {"url": "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"},
            {"url": "https://www.booking.com/hotel/es/jardines-de-nivaria.es.html"},
        ]

        st.info("⏳ Solicitando scraping a Bright Data...")
        response = requests.post(url, headers=headers, params=params, json=data)
        result = response.json()

        if "snapshot_id" in result:
            snapshot_id = result["snapshot_id"]
            st.success(f"✅ Snapshot generado: {snapshot_id}")
            time.sleep(6)  # Esperar a que los datos estén disponibles

            result_url = f"https://api.brightdata.com/datasets/v3/data?dataset_id={params['dataset_id']}&snapshot_id={snapshot_id}"
            res = requests.get(result_url, headers=headers)

            if res.status_code == 200:
                hoteles = res.json()
                st.subheader("🏨 Hoteles encontrados:")
                for hotel in hoteles:
                    nombre = hotel.get("title")
                    direccion = hotel.get("address")
                    puntuacion = hotel.get("review_score")

                    if nombre:
                        st.markdown(f"### 🏨 {nombre}")
                    if direccion:
                        st.write(f"📍 {direccion}")
                    if puntuacion:
                        st.write(f"⭐ {puntuacion}")
                    st.markdown("---")
            else:
                st.error(f"❌ Error al obtener los datos: {res.status_code}")
                st.code(res.text)
        else:
            st.error("❌ No se generó snapshot. Revisa el dataset ID o formato de URLs.")
            st.code(result)
