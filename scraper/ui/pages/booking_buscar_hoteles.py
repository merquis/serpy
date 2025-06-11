


"""Página de UI para Búsqueda en Booking.com""" 
import streamlit as st
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.booking_buscar_hoteles_service import BookingBuscarHotelesService
from services.booking_extraer_datos_service import BookingExtraerDatosService
from services.drive_service import DriveService
from services.simple_image_download import SimpleImageDownloadService
from repositories.mongo_repository import MongoRepository
from config import settings

class BookingBuscarHotelesPage:
    """Página para buscar hoteles en Booking.com con parámetros"""
    
    def __init__(self):
        self.search_service = BookingBuscarHotelesService()
        self.booking_service = BookingExtraerDatosService()
        self.drive_service = DriveService()
        self.image_download_service = SimpleImageDownloadService()
        self._mongo_repo = None  # Inicializar solo cuando se necesite
        self._init_session_state()
    
    def get_mongo_repo(self):
        """Lazy loading de MongoDB - solo se conecta cuando se necesita"""
        if self._mongo_repo is None:
            try:
                self._mongo_repo = MongoRepository(
                    uri=settings.mongodb_uri,
                    db_name=settings.mongodb_database
                )
            except Exception as e:
                st.error(f"Error conectando a MongoDB: {str(e)}")
                raise
        return self._mongo_repo
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "booking_search_results" not in st.session_state:
            st.session_state.booking_search_results = None
        if "booking_search_export_filename" not in st.session_state:
            st.session_state.booking_search_export_filename = "busqueda_booking.json"
        if "reset_form" not in st.session_state:
            st.session_state.reset_form = False
        if "last_mongo_id" not in st.session_state:
            st.session_state.last_mongo_id = None
        if "show_mongo_success" not in st.session_state:
            st.session_state.show_mongo_success = False
    
    def _on_checkin_change(self):
        """Callback cuando cambia la fecha de entrada"""
        # Marcar que necesitamos actualizar el checkout
        st.session_state['update_checkout'] = True
    
    def render(self):
        """Renderiza la página completa"""
        st.title("🔍 Búsqueda en Booking.com")
        st.markdown("### 🏨 Busca hoteles con parámetros personalizados")
        
        # Resetear campos si el flag está activo (antes de renderizar widgets)
        if "form_reset_count" not in st.session_state:
            st.session_state.form_reset_count = 0

        if st.session_state.get("reset_form", False):
            st.session_state.booking_search_results = None
            st.session_state.form_reset_count += 1
            keys_to_clear = [
                "destination_input", "checkin_input", "checkout_input",
                "adults_input", "children_input", "rooms_input",
                "stars_input", "min_score_input", "meal_plan_input",
                "pets_input", "max_results_input", "natural_filter_input",
                "extract_data_checkbox"
            ]
            for i in range(10):
                keys_to_clear.append(f"child_age_{i}")
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.reset_form = False

        # Eliminar mensaje de MongoDB de la cabecera si está pendiente
        # (Eliminado para que el mensaje sea realmente persistente)
        
        # Formulario de búsqueda
        search_params = self._render_search_form()
        
        # Botones de búsqueda
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🔍 Buscar Hoteles", type="primary", use_container_width=True):
                self._perform_search(search_params)
        
        with col2:
            if st.button("🔄 Nueva búsqueda", type="secondary", use_container_width=True):
                st.session_state.reset_form = True
                st.rerun()
        
        # Mostrar resultados si existen
        if st.session_state.booking_search_results:
            self._render_results_section()
    
    def _render_search_form(self) -> Dict[str, Any]:
        """Renderiza el formulario de búsqueda"""
        params = {}
        
        # Resetear flag si estaba activo
        if st.session_state.get('reset_form', False):
            st.session_state.reset_form = False
        
        # Destino y fechas en la misma línea
        col1, col2, col3 = st.columns([3, 1, 1])  # 60%, 20%, 20%
        
        with col1:
            params['destination'] = st.text_input(
                "📍 Destino",
                value="",
                placeholder="Escribe ciudad, región o lugar...",
                help="Ciudad, región o lugar de búsqueda",
                key=f"destination_input_{st.session_state.form_reset_count}"
            )
        
        with col2:
            checkin_key = f"checkin_input_{st.session_state.form_reset_count}"
            
            # Valor por defecto para checkin
            checkin_default = st.session_state.get(checkin_key, datetime.now())
            
            checkin_date = st.date_input(
                "📅 Fecha de entrada",
                value=checkin_default,
                min_value=datetime.now(),
                key=checkin_key,
                on_change=self._on_checkin_change
            )
            
            params['checkin'] = checkin_date.strftime('%Y-%m-%d')
        
        with col3:
            checkout_key = f"checkout_input_{st.session_state.form_reset_count}"
            
            # Si necesitamos actualizar el checkout por cambio en checkin
            if st.session_state.get('update_checkout', False):
                # Calcular nuevo checkout
                checkout_default = checkin_date + timedelta(days=1)
                # Limpiar el flag
                st.session_state['update_checkout'] = False
                # Eliminar el valor anterior del session state si existe
                if checkout_key in st.session_state:
                    del st.session_state[checkout_key]
            else:
                # Usar el valor del session state si existe, sino usar checkin + 1 día
                checkout_default = st.session_state.get(checkout_key, checkin_date + timedelta(days=1))
            
            params['checkout'] = st.date_input(
                "📅 Fecha de salida",
                value=checkout_default,
                min_value=checkin_date + timedelta(days=1),
                key=checkout_key
            ).strftime('%Y-%m-%d')
        
        # Ocupación
        st.subheader("👥 Ocupación")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            params['adults'] = st.number_input(
                "Adultos",
                min_value=1,
                max_value=30,
                value=2,
                key=f"adults_input_{st.session_state.form_reset_count}"
            )
        
        with col2:
            params['children'] = st.number_input(
                "Niños",
                min_value=0,
                max_value=10,
                value=0,
                key=f"children_input_{st.session_state.form_reset_count}"
            )
        
        with col3:
            params['rooms'] = st.number_input(
                "Habitaciones",
                min_value=1,
                max_value=30,
                value=1,
                key=f"rooms_input_{st.session_state.form_reset_count}"
            )
        
        # Edades de los niños
        if params['children'] > 0:
            st.write("🧒 Edades de los niños:")
            children_ages = []
            cols = st.columns(min(params['children'], 5))
            for i in range(params['children']):
                with cols[i % 5]:
                    age = st.number_input(
                        f"Niño {i+1}",
                        min_value=0,
                        max_value=17,
                        value=5,
                        key=f"child_age_{i}_{st.session_state.form_reset_count}"
                    )
                    children_ages.append(age)
            params['children_ages'] = children_ages
        
        # Filtros
        st.subheader("🎯 Filtros")
        
        # Tipo de alojamiento, Categoría y Ordenar por en una fila
        col1, col2, col3 = st.columns([1, 1, 1])

        # Tipo de alojamiento
        with col1:
            accommodation_types = {
                "Hotel": 204,
                "Apartamento": 201,
                "Casa o chalet": 220,
                "Villa": 213,
                "Bed and breakfast": 214,
                "Resort": 208,
                "Hostal o pensión": 216,
                "Camping": 222,
                "Albergue": 203
            }
            selected_type = st.selectbox(
                "🏨 Tipo de alojamiento",
                options=list(accommodation_types.keys()),
                index=0,
                key=f"accommodation_type_input_{st.session_state.form_reset_count}"
            )
            params["accommodation_type"] = accommodation_types[selected_type]

        with col3:
            order_options = {
                "bayesian_review_score": "Más valorados",
                "price": "Precio más bajo primero",
                "price_descending": "Precio más alto primero",
                "class_descending": "Categoría más alta primero",
                "class_ascending": "Categoría más baja primero",
                "class_and_price": "Categoría mayor con menor precio",
                "distance_from_landmark": "Cerca del centro de la ciudad"
            }
            params['order'] = st.selectbox(
                "🔄 Ordenar por",
                options=list(order_options.keys()),
                index=list(order_options.keys()).index("class_and_price"),
                format_func=lambda x: order_options[x],
                key=f"order_input_{st.session_state.form_reset_count}"
            )
        
        # Estrellas
        with col2:
            stars_options = st.multiselect(
                "⭐ Categoría (estrellas)",
                options=[1, 2, 3, 4, 5],
                default=[4, 5],
                key=f"stars_input_{st.session_state.form_reset_count}"
            )
            params['stars'] = stars_options
        
        # Segunda fila: Puntuación mínima, Régimen, mascotas y número de hoteles
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            params['min_score'] = st.selectbox(
                "📊 Puntuación mínima",
                options=['Sin filtro', '7.0', '8.0', '9.0'],
                index=2,  # Por defecto 8.0
                key=f"min_score_input_{st.session_state.form_reset_count}"
            )
            if params['min_score'] == 'Sin filtro':
                params['min_score'] = None

        with col2:
            meal_plan_options = {
                'desayuno_incluido': 'Desayuno incluido',
                'media_pension': 'Media pensión',
                'pension_completa': 'Pensión completa',
                'todo_incluido': 'Todo incluido'
            }
            selected_meal_plans = st.multiselect(
                "🍽️ Régimen alimenticio",
                options=list(meal_plan_options.keys()),
                default=[],  # Sin selección por defecto
                format_func=lambda x: meal_plan_options[x],
                key=f"meal_plan_input_{st.session_state.form_reset_count}_row2"
            )
            if selected_meal_plans:
                params['meal_plan'] = selected_meal_plans

        with col3:
            # Select para mascotas
            pets_option = st.selectbox(
                "🐾 Se admiten mascotas",
                options=['No', 'Sí'],
                index=0,  # Por defecto "No"
                help="Filtrar solo hoteles que admiten mascotas",
                key=f"pets_input_{st.session_state.form_reset_count}"
            )
            # Convertir a booleano para el parámetro
            params['pets_allowed'] = (pets_option == 'Sí')

        with col4:
            # Número de resultados como input numérico
            params['max_results'] = st.number_input(
                "📊 Número máximo de hoteles",
                min_value=1,
                max_value=100,
                value=10,  # Por defecto 10
                step=1,
                help="Número de URLs de hoteles que se extraerán de los resultados",
                key=f"max_results_input_{st.session_state.form_reset_count}"
            )

        # Barra de precios (slider)
        st.markdown("#### 💶 Tu presupuesto (por noche)")
        price_min, price_max = st.slider(
            "Selecciona el rango de precios (€ por noche)",
            min_value=0,
            max_value=1450,
            value=(0, 1450),
            step=10,
            format="€%d",
            key=f"price_slider_{st.session_state.form_reset_count}"
        )
        st.caption(f"€ {price_min} - € {price_max}")
        params['price_min'] = price_min
        params['price_max'] = price_max

        # Mostrar URL generada
        with st.expander("🔗 Ver URL de búsqueda generada"):
            preview_url = self.search_service.build_search_url(params)
            st.code(preview_url, language="text")
            st.caption("Esta es la URL que se utilizará para la búsqueda")

        # Filtro inteligente de lenguaje natural (justo antes del botón)
        st.markdown("### 🤖 Filtros inteligentes")
        params['natural_language_filter'] = st.text_area(
            "¿Qué estás buscando?",
            placeholder="Escribe en lenguaje natural lo que buscas, por ejemplo: '1 y 2 estrellas', 'hoteles con piscina', 'cerca de la playa', etc.",
            height=80,
            help="Este texto se transferirá al filtro inteligente de Booking.com",
            key=f"natural_filter_input_{st.session_state.form_reset_count}"
        )

        # Checkbox para extraer información de URLs
        params['extract_hotel_data'] = st.checkbox(
            "🔍 Extraer información URLs",
            value=False,
            help="Si está marcado, se extraerán los datos completos de cada hotel encontrado (nombre, servicios, imágenes, etc.)",
            key=f"extract_data_checkbox_{st.session_state.form_reset_count}"
        )

        return params
    
    def _perform_search(self, search_params: Dict[str, Any]):
        """Ejecuta la búsqueda con los parámetros especificados"""
        # Contenedor de progreso
        progress_container = st.empty()
        
        def update_progress(info: Dict[str, Any]):
            progress_container.info(info.get("message", "Procesando..."))
        
        extract_data = search_params.get('extract_hotel_data', False)
        
        with LoadingSpinner.show(f"Buscando hoteles en Booking..."):
            try:
                # Ejecutar búsqueda asíncrona
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Primero ejecutar la búsqueda
                search_results = loop.run_until_complete(
                    self.search_service.search_hotels(
                        search_params,
                        max_results=search_params.get('max_results', 15),
                        progress_callback=update_progress,
                        mongo_repo=None  # No guardar en MongoDB todavía
                    )
                )
                
                if search_results.get("error"):
                    Alert.error(f"Error en la búsqueda: {search_results['error']}")
                    st.session_state.booking_search_results = search_results
                    progress_container.empty()
                    st.rerun()
                    return
                
                # Si el checkbox está marcado, extraer datos completos
                if extract_data:
                    hotels = search_results.get("hotels", [])
                    hotel_urls = [h.get('url_arg', h.get('url', '')) for h in hotels if h.get('url_arg') or h.get('url')]
                    
                    if hotel_urls:
                        progress_container.info("🔍 Extrayendo datos completos de los hoteles...")
                        
                        # Función de progreso para la extracción
                        def extraction_progress(info: Dict[str, Any]):
                            progress_container.info(info.get("message", "Extrayendo datos..."))
                        
                        # Ejecutar extracción de datos
                        extracted_results = loop.run_until_complete(
                            self.booking_service.scrape_hotels(
                                hotel_urls,
                                progress_callback=extraction_progress
                            )
                        )
                        
                        # Filtrar hoteles exitosos
                        successful_hotels = [r for r in extracted_results if not r.get("error")]
                        
                        if successful_hotels:
                            # Guardar en colección hotel-booking
                            progress_container.info("💾 Guardando datos en MongoDB...")
                            
                            if len(successful_hotels) > 1:
                                inserted_ids = self.mongo_repo.insert_many(
                                    successful_hotels,
                                    collection_name="hotel-booking"
                                )
                                # Crear lista detallada de hoteles guardados
                                hotel_list = []
                                for i, (hotel, mongo_id) in enumerate(zip(successful_hotels, inserted_ids)):
                                    hotel_name = hotel.get("nombre_alojamiento", f"Hotel {i+1}")
                                    hotel_list.append(f"• {mongo_id}: {hotel_name}")
                                
                                st.session_state.last_mongo_id = f"{len(inserted_ids)} hoteles guardados"
                                st.session_state.hotel_details_list = hotel_list
                            else:
                                inserted_id = self.mongo_repo.insert_one(
                                    successful_hotels[0],
                                    collection_name="hotel-booking"
                                )
                                hotel_name = successful_hotels[0].get("nombre_alojamiento", "Hotel")
                                st.session_state.last_mongo_id = str(inserted_id)
                                st.session_state.hotel_details_list = [f"• {inserted_id}: {hotel_name}"]
                            
                            # Iniciar descarga de imágenes
                            progress_container.info("🖼️ Iniciando descarga de imágenes...")
                            
                            if len(successful_hotels) > 1:
                                for i, mongo_id in enumerate(inserted_ids):
                                    try:
                                        database_name = st.secrets["mongodb"]["db"]
                                        loop.run_until_complete(
                                            self.image_download_service.trigger_download(
                                                mongo_id,
                                                database_name=database_name,
                                                collection_name="hotel-booking"
                                            )
                                        )
                                    except Exception as e:
                                        st.warning(f"Error al descargar imágenes del hotel {i+1}: {str(e)}")
                            else:
                                try:
                                    database_name = st.secrets["mongodb"]["db"]
                                    loop.run_until_complete(
                                        self.image_download_service.trigger_download(
                                            inserted_id,
                                            database_name=database_name,
                                            collection_name="hotel-booking"
                                        )
                                    )
                                except Exception as e:
                                    st.warning(f"Error al descargar imágenes: {str(e)}")
                            
                            # Guardar resultados extraídos en session state
                            st.session_state.booking_search_results = extracted_results
                            st.session_state.show_mongo_success = True
                        else:
                            Alert.warning("No se pudieron extraer datos de ningún hotel")
                            st.session_state.booking_search_results = search_results
                    else:
                        Alert.warning("No se encontraron URLs válidas para extraer")
                        st.session_state.booking_search_results = search_results
                else:
                    # Checkbox desmarcado: comportamiento normal (guardar búsqueda)
                    # Verificar que hay un proyecto activo
                    if not st.session_state.get("proyecto_nombre"):
                        Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
                        st.session_state.booking_search_results = search_results
                        progress_container.empty()
                        st.rerun()
                        return
                    
                    # Obtener el nombre del proyecto activo y normalizarlo
                    proyecto_activo = st.session_state.proyecto_nombre
                    
                    # Importar la función de normalización y aplicarla
                    from config.settings import normalize_project_name
                    proyecto_normalizado = normalize_project_name(proyecto_activo)
                    
                    # Crear nombre de colección con proyecto normalizado
                    collection_name = f"{proyecto_normalizado}_urls_booking"
                    
                    # Agregar metadatos del proyecto
                    import copy
                    from datetime import datetime
                    
                    search_results_with_metadata = copy.deepcopy(search_results)
                    timestamp = datetime.now().isoformat()
                    search_results_with_metadata["_guardado_automatico"] = timestamp
                    search_results_with_metadata["_proyecto_activo"] = proyecto_activo
                    search_results_with_metadata["_proyecto_normalizado"] = proyecto_normalizado
                    
                    # Guardar en colección del proyecto
                    mongo_id = self.mongo_repo.insert_one(
                        search_results_with_metadata,
                        collection_name=collection_name
                    )
                    search_results["mongo_id"] = mongo_id
                    st.session_state.booking_search_results = search_results
                    st.session_state.last_mongo_id = f"Guardado en {collection_name} con ID: {str(mongo_id)}"
                    st.session_state.show_mongo_success = True
                
                progress_container.empty()
                st.rerun()
                
            except Exception as e:
                Alert.error(f"Error durante la búsqueda: {str(e)}")
            finally:
                loop.close()
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        results = st.session_state.booking_search_results
        
        if not results:
            return
        
        # Detectar si son resultados extraídos (lista de hoteles con datos completos) o búsqueda normal
        is_extracted_data = isinstance(results, list) and len(results) > 0 and results[0].get("nombre_alojamiento") is not None
        
        # Información de la búsqueda
        if is_extracted_data:
            st.subheader("📊 Resultados de extracción de datos")
        else:
            st.subheader("📊 Resultados de la búsqueda")

        # Mensaje de subida a MongoDB justo debajo del título de resultados
        if st.session_state.get('show_mongo_success', False) and st.session_state.get('last_mongo_id'):
            st.success(f"✅ Datos guardados en MongoDB: {st.session_state.last_mongo_id}")
            
            # Mostrar lista detallada de hoteles si está disponible
            if st.session_state.get('hotel_details_list'):
                with st.expander("📋 Ver detalles de hoteles guardados", expanded=False):
                    for hotel_detail in st.session_state.hotel_details_list:
                        st.write(hotel_detail)

        # Métricas diferentes según el tipo de resultado
        if is_extracted_data:
            successful = [r for r in results if not r.get("error")]
            failed = [r for r in results if r.get("error")]
            total_images = sum(len(r.get("imagenes", [])) for r in successful)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total procesados", len(results))
            with col2:
                st.metric("Exitosos", len(successful))
            with col3:
                st.metric("Con errores", len(failed))
            with col4:
                st.metric("Imágenes extraídas", total_images)
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Hoteles encontrados", len(results.get("hotels", [])))
            with col2:
                st.metric("Parámetros de búsqueda", len(results.get("search_params", {})))
            with col3:
                if results.get("fecha_busqueda"):
                    fecha = datetime.fromisoformat(results["fecha_busqueda"].replace('Z', '+00:00'))
                    st.metric("Búsqueda realizada", fecha.strftime("%H:%M:%S"))

            # URL de búsqueda (solo para resultados de búsqueda normal)
            with st.expander("🔗 URL de búsqueda utilizada"):
                # URL original
                st.markdown("**URL inicial:**")
                st.code(results.get("search_url", ""), language="text")
                
                # URL después de aplicar filtros inteligentes (si existe)
                if results.get("search_params", {}).get("natural_language_filter"):
                    if results.get("filtered_url"):
                        st.markdown("**URL después de aplicar filtros inteligentes:**")
                        st.code(results.get("filtered_url", ""), language="text")
                        st.caption(f"✅ Filtro aplicado correctamente: '{results.get('search_params', {}).get('natural_language_filter')}'")
                    elif results.get("filter_warning"):
                        st.warning(f"⚠️ {results.get('filter_warning')}")
                        st.caption(f"Filtro intentado: '{results.get('search_params', {}).get('natural_language_filter')}'")
        
        # Opciones de exportación
        self._render_export_options()
        
        # Mostrar hoteles encontrados
        if is_extracted_data:
            self._display_extracted_hotels(results)
        else:
            self._display_hotels(results.get("hotels", []))
    
    def _render_export_options(self):
        """Renderiza las opciones de exportación"""
        st.session_state.booking_search_export_filename = st.text_input(
            "📄 Nombre del archivo para exportar:",
            value=st.session_state.booking_search_export_filename
        )

        col1, col2 = st.columns(2)

        with col1:
            self._render_download_button()

        with col2:
            self._render_drive_upload_button()
    
    def _render_download_button(self):
        """Renderiza el botón de descarga"""
        results = st.session_state.booking_search_results
        
        # Preparar los resultados para JSON (convertir ObjectIds a strings)
        results_for_json = self._prepare_results_for_json(results)
        
        json_bytes = json.dumps(
            results_for_json,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")
        
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name=st.session_state.booking_search_export_filename,
            mime="application/json"
        )
    
    def _render_drive_upload_button(self):
        """Renderiza el botón de subida a Drive"""
        if Button.secondary("Subir a Drive", icon="☁️"):
            if "proyecto_id" not in st.session_state:
                Alert.warning("Selecciona un proyecto en la barra lateral")
                return
            
            try:
                results = st.session_state.booking_search_results
                
                # Preparar los resultados para JSON (convertir ObjectIds a strings)
                results_for_json = self._prepare_results_for_json(results)
                
                json_bytes = json.dumps(
                    results_for_json,
                    ensure_ascii=False,
                    indent=2
                ).encode("utf-8")
                
                # Obtener carpeta
                folder_id = self.drive_service.get_or_create_folder(
                    "busquedas booking",
                    st.session_state.proyecto_id
                )
                
                # Subir archivo
                link = self.drive_service.upload_file(
                    st.session_state.booking_search_export_filename,
                    json_bytes,
                    folder_id
                )
                
                if link:
                    Alert.success(f"Archivo subido: [Ver en Drive]({link})")
                else:
                    Alert.error("Error al subir archivo")
                    
            except Exception as e:
                Alert.error(f"Error al subir a Drive: {str(e)}")
    
    
    def _display_hotels(self, hotels: List[Dict[str, Any]]):
        """Muestra los hoteles encontrados (resultados de búsqueda)"""
        if not hotels:
            st.info("No se encontraron hoteles")
            return
        
        # Solo mostrar el título con el número de hoteles
        st.subheader(f"🏨 Hoteles encontrados ({len(hotels)})")
        
        # Mostrar directamente el JSON completo expandido
        DataDisplay.json(
            self._prepare_results_for_json(st.session_state.booking_search_results),
            title="JSON Completo de la Búsqueda",
            expanded=True
        )
    
    def _display_extracted_hotels(self, extracted_data: List[Dict[str, Any]]):
        """Muestra los datos extraídos de hoteles (formato de extracción)"""
        if not extracted_data:
            st.info("No se extrajeron datos")
            return
        
        # Usar la misma función de preparación que en "Extraer hoteles booking"
        json_export = self._prepare_results_for_extraction_json(extracted_data)
        
        # Mostrar el JSON con el formato de extracción
        DataDisplay.json(
            json_export,
            title="JSON Completo (estructura exportación)",
            expanded=True
        )
    
    def _prepare_results_for_extraction_json(self, data):
        """
        Prepara los resultados para serialización JSON en formato de extracción.
        Saca los campos comunes fuera del array de hoteles (igual que en extraer datos).
        """
        # Campos comunes a extraer fuera
        campos_comunes = [
            "fecha_scraping",
            "busqueda_checkin",
            "busqueda_checkout",
            "busqueda_adultos",
            "busqueda_ninos",
            "busqueda_habitaciones",
            "busqueda_tipo_destino",
            "nombre_alojamiento",
            "tipo_alojamiento",
            "direccion",
            "codigo_postal",
            "ciudad",
            "pais"
        ]

        # Si es una lista de hoteles, buscar los campos comunes en el primero
        if isinstance(data, list) and data:
            primer = data[0]
            comunes = {k: primer[k] for k in campos_comunes if k in primer}
            # Eliminar los campos comunes de cada hotel
            hoteles = []
            for h in data:
                h2 = {k: v for k, v in h.items() if k not in campos_comunes}
                hoteles.append(h2)
            return {
                "campos_comunes": comunes,
                "hoteles": hoteles
            }
        elif isinstance(data, dict):
            return {k: self._prepare_results_for_extraction_json(v) for k, v in data.items()}
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId':
            return str(data)
        else:
            return data
    
    def _prepare_results_for_json(self, data):
        """Prepara los resultados para serialización JSON convirtiendo ObjectIds a strings y eliminando _id/mongo_id"""
        if isinstance(data, dict):
            # Eliminar los campos "_id" y "mongo_id" si existen
            return {k: self._prepare_results_for_json(v) for k, v in data.items() if k not in ["_id", "mongo_id"]}
        elif isinstance(data, list):
            return [self._prepare_results_for_json(item) for item in data]
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId':
            return str(data)
        else:
            return data
