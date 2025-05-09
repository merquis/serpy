# modules/scrapers/scraping_booking.py

import streamlit as st
import requests
import time

def render_scraping_booking():
    st.header("📦 Scraping de Hoteles en Booking (Bright Data API)")

    st.markdown("### ✍️ Parámetros de búsqueda")
    location = st.text_input("📍 Ciudad destino", "Tenerife")
    check_in = st.date_input("📅 Fecha de entrada")
    check_out = st.date_input("📅 Fecha de salida")
    adults = st.number_input("👤 Adultos", min_value=1, value=2)
    children = st.number_input("🧒 Niños", min_value=0, value=1)
    rooms = st.number_input("🛏️ Habitaciones", min_value=1, value=1)
    country = st.text_input("🌍 País (código ISO)", "ES")
    currency = st.text_input("💱 Moneda (opcional)", "")

    if st.button("📥 Obtener datos de los hoteles"):
        url = "https://api.brightdata.com/datasets/v3/trigger"
        headers = {
            "Authorization": f"Bearer {st.secrets['brightdata_booking']['token']}",
            "Content-Type": "application/json",
        }
        params = {
            "dataset_id": "gd_m4bf7a917zfezv9d5",
            "include_errors": "true",
        }

        data = [
            {
                "url": "https://www.booking.com",
                "location": location,
                "check_in": check_in.strftime("%Y-%m-%dT00:00:00.000Z"),
                "check_out": check_out.strftime("%Y-%m-%dT00:00:00.000Z"),
                "adults": adults,
                "children": children,
                "rooms": rooms,
                "country": country,
                "currency": currency
            }
        ]

        st.info("⏳ Enviando solicitud a Bright Data...")
        response = requests.post(url, headers=headers, params=params, json=data)
        result = response.json()

        if "snapshot_id" in result:
            snapshot_id = result["snapshot_id"]
            st.success(f"📦 Snapshot generado: {snapshot_id}")
            time.sleep(90)

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
