# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time

def render_scraping_booking():
    st.header("📦 Scraping de Hoteles en Booking (Bright Data API)")

    urls_default = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    input_urls = st.text_area("🔗 Introduce URLs de hoteles (una por línea):", value=urls_default)

    if st.button("📥 Obtener datos de los hoteles"):
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {st.secrets['brightdata_booking']['token']}",
            "Content-Type": "application/json",
        }
        params = {
            "dataset_id": "gd_m5mbdl081229ln6t4a",
            "include_errors": "true",
        }

        urls = [line.strip() for line in input_urls.strip().splitlines() if line.strip()]
        data = [{"url": u} for u in urls]

        st.info("⏳ Enviando solicitud a Bright Data...")
        response = requests.post(url, headers=headers, params=params, json=data)
        result = response.json()

        if "snapshot_id" in result:
            snapshot_id = result["snapshot_id"]
            st.success(f"📦 Snapshot generado: {snapshot_id}")
            time.sleep(90)  # espera de 1 minuto

            result_url = f"https://api.brightdata.com/datasets/v3/data?dataset_id={params['dataset_id']}&snapshot_id={snapshot_id}"
            res = requests.get(result_url, headers=headers)

            if res.status_code == 200:
                try:
                    hoteles = res.json()
                    st.subheader("📨 JSON completo de respuesta:")
                    st.json(hoteles)
                    st.subheader("🏨 Información de los hoteles:")
                    for hotel in hoteles:
                        nombre = hotel.get("title", "Nombre no disponible")
                        direccion = hotel.get("address")
                        puntuacion = hotel.get("review_score")
                        enlace = hotel.get("url")

                        st.markdown(f"### 🏨 [{nombre}]({enlace})")
                        if direccion:
                            st.write(f"📍 {direccion}")
                        if puntuacion:
                            st.write(f"⭐ {puntuacion}")
                        st.markdown("---")
                except Exception as e:
                    st.error("❌ Error al procesar el JSON")
                    st.code(res.text)
            else:
                st.error(f"❌ Error al recuperar los datos: {res.status_code}")
                st.code(res.text)
        else:
            st.error("❌ No se generó snapshot.")
            st.code(result)
