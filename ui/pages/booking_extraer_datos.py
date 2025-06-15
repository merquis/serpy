import streamlit as st
from services.booking_extraer_datos_service import BookingExtraerDatosService

class BookingExtraerDatosPage:
    def __init__(self):
        self.service = BookingExtraerDatosService()

    def render(self):
        st.title("Extraer datos de hoteles de Booking.com")

        url = st.text_input("URL del hotel de Booking.com:")

        if st.button("Extraer datos"):
            if url:
                st.info("Extrayendo datos...")
                try:
                    hotel_data = self.service._parse_hotel_html(url)
                    if hotel_data:
                        st.write("Datos del hotel:")
                        st.write(hotel_data)
                        st.write(f"Rango de precios: {hotel_data.get('rango_precios', 'No disponible')}")
                    else:
                        st.write("No se encontraron datos")
                except Exception as e:
                    st.error(f"Error al extraer datos: {e}")
            else:
                st.warning("Por favor, introduce una URL")
