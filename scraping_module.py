def render_scraping():
    """
    Renderiza la interfaz de usuario (UI) para realizar el scraping.
    Incluye selección de proyecto, etiquetas, campos de búsqueda y acciones.
    """
    st.title("TripToIslands · Panel Admin")

    # Inicialización de variables de sesión
    if 'resultados' not in st.session_state:
        st.session_state.resultados = None
    if 'nombre_archivo' not in st.session_state:
        st.session_state.nombre_archivo = None
    if 'json_bytes' not in st.session_state:
        st.session_state.json_bytes = None

    # ============================
    # SELECCIÓN DEL PROYECTO
    # ============================
    proyecto = st.sidebar.selectbox("Seleccione proyecto:", ["TripToIslands", "MiBebeBello"], index=0, key="proyecto_selectbox")

    carpeta_id = {
        "TripToIslands": "1QS2fnsrlHxS3ZeLYvhzZqnuzx1OdRJWR",
        "MiBebeBello": "1ymfS5wfyPoPY_b9ap1sWjYrfxlDHYycI"
    }[proyecto]

    # ============================
    # SELECCIÓN DEL MÓDULO
    # ============================
    st.sidebar.markdown("**Selecciona un módulo**")
    opcion = st.sidebar.selectbox("Selecciona un módulo", ["Scraping"], key="modulo_selectbox")

    # ============================
    # SELECCIÓN DE ETIQUETAS
    # ============================
    st.sidebar.markdown("**Extraer etiquetas**")
    col_a, col_b, col_c = st.sidebar.columns(3)
    etiquetas = []
    if col_a.checkbox("H1", key="h1_checkbox"): etiquetas.append("h1")
    if col_b.checkbox("H2", key="h2_checkbox"): etiquetas.append("h2")
    if col_c.checkbox("H3", key="h3_checkbox"): etiquetas.append("h3")

    # ============================
    # CAMPOS DE BÚSQUEDA
    # ============================
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 Escribe tu búsqueda en Google (separa con comas)")
    with col2:
        num_results = st.selectbox("📄 Nº resultados", options=list(range(10, 101, 10)), index=0, key="num_resultados")

    # ============================
    # BOTONES DE ACCIÓN
    # ============================
    col_btn, col_export, col_drive, col_reset = st.columns([1, 1, 1, 1])

    with col_btn:
        buscar = st.button("Buscar")

    # Solo mostrar el botón de "Nueva búsqueda" si hay resultados previos
    with col_reset:
        if st.session_state.resultados:
            if st.button("🔄 Nueva búsqueda"):
                st.session_state.resultados = None
                st.session_state.nombre_archivo = None
                st.session_state.json_bytes = None
                st.experimental_rerun()

    # ============================
    # EJECUCIÓN DEL SCRAPING
    # ============================
    if buscar and query:
        with st.spinner("Consultando Google y extrayendo etiquetas..."):
            resultados = testear_proxy_google(query, int(num_results), etiquetas)
            nombre_archivo = "-".join([t.strip() for t in query.split(",")]) + ".json"
            json_bytes = json.dumps(resultados, ensure_ascii=False, indent=2).encode('utf-8')

            st.session_state.resultados = resultados
            st.session_state.nombre_archivo = nombre_archivo
            st.session_state.json_bytes = json_bytes

    # ============================
    # MOSTRAR RESULTADOS
    # ============================
    if st.session_state.resultados:
        st.subheader("📦 Resultados en formato JSON enriquecido")
        st.json(st.session_state.resultados)

        with col_export:
            st.download_button(
                label="⬇️ Exportar JSON",
                data=st.session_state.json_bytes,
                file_name=st.session_state.nombre_archivo,
                mime="application/json"
            )

        with col_drive:
            if st.button("📤 Subir a Google Drive"):
                with st.spinner("Subiendo archivo a Google Drive..."):
                    enlace = subir_json_a_drive(
                        st.session_state.nombre_archivo,
                        st.session_state.json_bytes,
                        carpeta_id
                    )
                    if enlace:
                        st.success(f"✅ Subido correctamente: [Ver en Drive]({enlace})")
                    else:
                        st.error("❌ Error al subir el archivo a Google Drive.")
