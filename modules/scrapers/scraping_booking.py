# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time

def render_scraping_booking():
    st.header("Scraping Booking desde URLs específicas – Bright Data API")

    urls = st.text_area("✍️ Pega una o más URLs de Booking (una por línea)", """https://www.booking.com/hotel/es/jardines-de-nivaria.es.html
https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html""")

    if st.button("🔍 Obtener hoteles desde Bright Data"):
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {st.secrets['brightdata_booking']['token']}",
            "Content-Type": "application/json"
        }
        params = {
            "dataset_id": "gd_m5mbdl081229ln6t4a",
            "include_errors": "true"
        }

        data = [{"url": u.strip()} for u in urls.strip().splitlines() if u.strip()]

        st.info(f"🔄 Enviando {len(data)} URL(s) a Bright Data...")
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
                st.markdown("---")
        else:
            st.warning("No se devolvieron resultados aún.")
