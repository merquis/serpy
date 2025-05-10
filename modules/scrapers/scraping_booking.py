def render_scraping_booking():
    st.session_state["_called_script"] = "scraping_booking"
    st.title("🏨 Scraping de nombres de hoteles en Booking (modo urllib.request)")

    if "urls_input" not in st.session_state:
        st.session_state.urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html"
    if "resultados_json" not in st.session_state:
        st.session_state.resultados_json = []

    # Formulario
    st.session_state.urls_input = st.text_area(
        "📝 Pega una o varias URLs de Booking (una por línea):",
        st.session_state.urls_input,
        height=150
    )

    # Ahora 3 columnas desde el principio (aunque algunos botones estén vacíos al inicio)
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        buscar_btn = st.button("🔍 Scrapear nombre hotel", key="buscar_nombre_hotel")

    with col2:
        if st.session_state.resultados_json:
            nombre_archivo = "datos_hoteles_booking.json"
            json_bytes = json.dumps(st.session_state.resultados_json, ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                label="⬇️ Exportar JSON",
                data=json_bytes,
                file_name=nombre_archivo,
                mime="application/json",
                key="descargar_json"
            )

    with col3:
        if st.session_state.resultados_json:
            subir_a_drive_btn = st.button("☁️ Subir a Google Drive", key="subir_drive_booking")

    # Lógica después de hacer scraping
    if buscar_btn and st.session_state.urls_input:
        urls = [url.strip() for url in st.session_state.urls_input.split("\n") if url.strip()]
        with st.spinner("🔄 Scrapeando nombres de hoteles..."):
            resultados = obtener_datos_booking(urls)
            st.session_state.resultados_json = resultados

    # Lógica después de darle al botón subir
    if st.session_state.resultados_json and 'subir_a_drive_btn' in locals() and subir_a_drive_btn:
        with st.spinner("☁️ Subiendo JSON a Google Drive (cuenta de servicio)..."):
            if st.session_state.get("proyecto_id"):
                carpeta_principal = st.session_state["proyecto_id"]
                subcarpeta_id = obtener_o_crear_subcarpeta("scraper url hotel booking", carpeta_principal)

                if subcarpeta_id:
                    enlace = subir_json_a_drive(nombre_archivo, json_bytes, subcarpeta_id)
                    if enlace:
                        st.success(f"✅ Subido correctamente: [Ver archivo]({enlace})", icon="📁")
                    else:
                        st.error("❌ Error al subir el archivo a la subcarpeta.")
                else:
                    st.error("❌ No se pudo encontrar o crear la subcarpeta.")
            else:
                st.error("❌ No hay proyecto seleccionado en session_state['proyecto_id'].")

    # Mostrar resultados JSON
    if st.session_state.resultados_json:
        st.subheader("📦 Resultados obtenidos")
        st.json(st.session_state.resultados_json)
