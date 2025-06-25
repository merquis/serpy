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
import logging

logger = logging.getLogger(__name__)

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
        
        if "form_reset_count" not in st.session_state:
            st.session_state.form_reset_count = 0

        if st.session_state.get("reset_form", False):
            st.session_state.booking_search_results = None
            st.session_state.form_reset_count += 1
            keys_to_clear = [
                "destination_input", "checkin_input", "checkout_input",
                "adults_input", "children_input", "rooms_input",
                "stars_input", "min_score_input", "meal_plan_input",
                "pets_input", "max_images_input", "max_results_input", "natural_filter_input",
                "extract_data_checkbox"
            ]
            for i in range(10):
                keys_to_clear.append(f"child_age_{i}")
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.reset_form = False
        
        search_params = self._render_search_form()
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🔍 Buscar Hoteles", type="primary", use_container_width=True):
                self._perform_search(search_params)
        
        with col2:
            if st.button("🔄 Nueva búsqueda", type="secondary", use_container_width=True):
                st.session_state.reset_form = True
                st.rerun()
        
        if st.session_state.booking_search_results:
            self._render_results_section()
    
    def _render_search_form(self) -> Dict[str, Any]:
        params = {}
        
        if st.session_state.get('reset_form', False):
            st.session_state.reset_form = False
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            params['destination'] = st.text_input(
                "📍 Destino", value="", placeholder="Escribe ciudad, región o lugar...",
                help="Ciudad, región o lugar de búsqueda", key=f"destination_input_{st.session_state.form_reset_count}"
            )
        
        with col2:
            checkin_key = f"checkin_input_{st.session_state.form_reset_count}"
            checkin_default = st.session_state.get(checkin_key, datetime.now())
            checkin_date = st.date_input(
                "📅 Fecha de entrada", value=checkin_default, min_value=datetime.now(),
                key=checkin_key, on_change=self._on_checkin_change
            )
            params['checkin'] = checkin_date.strftime('%Y-%m-%d')
        
        with col3:
            checkout_key = f"checkout_input_{st.session_state.form_reset_count}"
            if st.session_state.get('update_checkout', False):
                checkout_default = checkin_date + timedelta(days=1)
                st.session_state['update_checkout'] = False
                if checkout_key in st.session_state:
                    del st.session_state[checkout_key]
            else:
                checkout_default = st.session_state.get(checkout_key, checkin_date + timedelta(days=1))
            params['checkout'] = st.date_input(
                "📅 Fecha de salida", value=checkout_default, min_value=checkin_date + timedelta(days=1),
                key=checkout_key
            ).strftime('%Y-%m-%d')
        
        st.subheader("👥 Ocupación")
        col1, col2, col3 = st.columns(3)
        with col1:
            params['adults'] = st.number_input("Adultos", min_value=1, max_value=30, value=2, key=f"adults_input_{st.session_state.form_reset_count}")
        with col2:
            params['children'] = st.number_input("Niños", min_value=0, max_value=10, value=0, key=f"children_input_{st.session_state.form_reset_count}")
        with col3:
            params['rooms'] = st.number_input("Habitaciones", min_value=1, max_value=30, value=1, key=f"rooms_input_{st.session_state.form_reset_count}")
        
        if params['children'] > 0:
            st.write("🧒 Edades de los niños:")
            children_ages = []
            cols = st.columns(min(params['children'], 5))
            for i in range(params['children']):
                with cols[i % 5]:
                    age = st.number_input(f"Niño {i+1}", min_value=0, max_value=17, value=5, key=f"child_age_{i}_{st.session_state.form_reset_count}")
                    children_ages.append(age)
            params['children_ages'] = children_ages
        
        st.subheader("🎯 Filtros")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            accommodation_types = {"Hotel": 204, "Apartamento": 201, "Casa o chalet": 220, "Villa": 213, "Bed and breakfast": 214, "Resort": 208, "Hostal o pensión": 216, "Camping": 222, "Albergue": 203}
            selected_type = st.selectbox("🏨 Tipo de alojamiento", options=list(accommodation_types.keys()), index=0, key=f"accommodation_type_input_{st.session_state.form_reset_count}")
            params["accommodation_type"] = accommodation_types[selected_type]
        with col3:
            order_options = {"bayesian_review_score": "Más valorados", "price": "Precio más bajo primero", "price_descending": "Precio más alto primero", "class_descending": "Categoría más alta primero", "class_ascending": "Categoría más baja primero", "class_and_price": "Categoría mayor con menor precio", "distance_from_landmark": "Cerca del centro de la ciudad"}
            params['order'] = st.selectbox("🔄 Ordenar por", options=list(order_options.keys()), index=list(order_options.keys()).index("class_and_price"), format_func=lambda x: order_options[x], key=f"order_input_{st.session_state.form_reset_count}")
        with col2:
            stars_options = st.multiselect("⭐ Categoría (estrellas)", options=[1, 2, 3, 4, 5], default=[4, 5], key=f"stars_input_{st.session_state.form_reset_count}")
            params['stars'] = stars_options
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            params['min_score'] = st.selectbox("📊 Puntuación mínima", options=['Sin filtro', '7.0', '8.0', '9.0'], index=2, key=f"min_score_input_{st.session_state.form_reset_count}")
            if params['min_score'] == 'Sin filtro': params['min_score'] = None
        with col2:
            meal_plan_options = {'desayuno_incluido': 'Desayuno incluido', 'media_pension': 'Media pensión', 'pension_completa': 'Pensión completa', 'todo_incluido': 'Todo incluido'}
            selected_meal_plans = st.multiselect("🍽️ Régimen alimenticio", options=list(meal_plan_options.keys()), default=[], format_func=lambda x: meal_plan_options[x], key=f"meal_plan_input_{st.session_state.form_reset_count}_row2")
            if selected_meal_plans: params['meal_plan'] = selected_meal_plans
        with col3:
            pets_option = st.selectbox("🐾 Se admiten mascotas", options=['No', 'Sí'], index=0, help="Filtrar solo hoteles que admiten mascotas", key=f"pets_input_{st.session_state.form_reset_count}")
            params['pets_allowed'] = (pets_option == 'Sí')
        with col4:
            params['max_images'] = st.number_input("🖼️ Número de imágenes", min_value=1, max_value=30, value=10, step=1, help="Número de imágenes que se extraerán de cada hotel", key=f"max_images_input_{st.session_state.form_reset_count}")
        with col5:
            params['max_results'] = st.number_input("📊 Número máximo de hoteles", min_value=1, max_value=100, value=10, step=1, help="Número de URLs de hoteles que se extraerán de los resultados", key=f"max_results_input_{st.session_state.form_reset_count}")

        st.markdown("#### 💶 Tu presupuesto (por noche)")
        price_min, price_max = st.slider("Selecciona el rango de precios (€ por noche)", min_value=0, max_value=1450, value=(0, 1450), step=10, format="€%d", key=f"price_slider_{st.session_state.form_reset_count}")
        st.caption(f"€ {price_min} - € {price_max}")
        params['price_min'] = price_min
        params['price_max'] = price_max

        with st.expander("🔗 Ver URL de búsqueda generada"):
            preview_url = self.search_service.build_search_url(params)
            st.code(preview_url, language="text")
            st.caption("Esta es la URL que se utilizará para la búsqueda")

        st.markdown("### 🤖 Filtros inteligentes")
        params['natural_language_filter'] = st.text_area("¿Qué estás buscando?", placeholder="Escribe en lenguaje natural lo que buscas, por ejemplo: '1 y 2 estrellas', 'hoteles con piscina', 'cerca de la playa', etc.", height=80, help="Este texto se transferirá al filtro inteligente de Booking.com", key=f"natural_filter_input_{st.session_state.form_reset_count}")
        
        params['extract_hotel_data'] = st.checkbox("🔍 Extraer información URLs", value=True, help="Si está marcado, se extraerán los datos completos de cada hotel encontrado (nombre, servicios, imágenes, etc.)", key=f"extract_data_checkbox_{st.session_state.form_reset_count}")
        
        # Mostrar slider de concurrencia solo si el checkbox está activado
        if params['extract_hotel_data']:
            params['max_concurrent'] = st.slider(
                "🔄 URLs concurrentes",
                min_value=1,
                max_value=20,
                value=5,
                help="Número de URLs a procesar simultáneamente. Más URLs = más rápido pero más recursos."
            )
            
            # Mostrar información sobre la concurrencia
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"🚀 Procesando {params['max_concurrent']} URLs a la vez")
            with col2:
                if params['max_concurrent'] <= 5:
                    st.success("✅ Velocidad conservadora")
                elif params['max_concurrent'] <= 10:
                    st.warning("⚡ Velocidad moderada")
                else:
                    st.error("🔥 Velocidad agresiva")
            with col3:
                # Estimar tiempo basado en el número máximo de resultados
                time_estimate = params.get('max_results', 10) / params['max_concurrent'] * 10  # ~10 segundos por URL
                st.metric("⏱️ Tiempo estimado", f"{time_estimate:.0f} seg")
        
        return params
    
    def _perform_search(self, search_params: Dict[str, Any]):
        progress_container = st.empty()
        def update_progress(info: Dict[str, Any]):
            progress_container.info(info.get("message", "Procesando..."))
        
        extract_data = search_params.get('extract_hotel_data', False)
        
        with LoadingSpinner.show(f"Buscando hoteles en Booking..."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                search_results = loop.run_until_complete(
                    self.search_service.search_hotels(
                        search_params, max_results=search_params.get('max_results', 15),
                        progress_callback=update_progress, mongo_repo=None
                    )
                )
                
                if search_results.get("error"):
                    Alert.error(f"Error en la búsqueda: {search_results['error']}")
                    st.session_state.booking_search_results = search_results
                    progress_container.empty()
                    st.rerun()
                    return
                
                if extract_data:
                    hotels = search_results.get("hotels", [])
                    hotel_urls = [h.get('url_arg', h.get('url', '')) for h in hotels if h.get('url_arg') or h.get('url')]
                    
                    if hotel_urls:
                        # Contenedor para mostrar el progreso detallado
                        progress_container.empty()
                        progress_detail_container = st.container()
                        
                        with progress_detail_container:
                            st.info(f"🔍 Extrayendo datos de {len(hotel_urls)} hoteles con {search_params.get('max_concurrent', 5)} URLs concurrentes")
                            
                            # Métricas de progreso
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                completed_metric = st.empty()
                                completed_metric.metric("✅ Completados", "0/0")
                            with col2:
                                processing_metric = st.empty()
                                processing_metric.metric("🔄 Procesando", "0")
                            with col3:
                                speed_metric = st.empty()
                                speed_metric.metric("⚡ Velocidad", "0 hoteles/min")
                            
                            # Barra de progreso
                            progress_bar = st.progress(0)
                            
                            # Contenedor para mostrar hoteles activos
                            st.markdown("---")
                            st.markdown("### 🌐 Hoteles procesándose actualmente:")
                            active_hotels_container = st.empty()
                            
                            # Tiempo de inicio
                            start_time = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
                        
                        def extraction_progress(info: Dict[str, Any]):
                            """Actualiza la visualización del progreso con detalles de cada hotel"""
                            try:
                                completed = info.get("completed", 0)
                                total = info.get("total", len(hotel_urls))
                                active_urls = info.get("active_urls", [])
                                concurrent = info.get("concurrent", 0)
                                
                                # Actualizar métricas
                                completed_metric.empty()
                                completed_metric.metric("✅ Completados", f"{completed}/{total}")
                                
                                processing_metric.empty()
                                processing_metric.metric("🔄 Procesando", concurrent)
                                
                                # Calcular velocidad
                                if completed > 0 and start_time > 0:
                                    elapsed_time = asyncio.get_event_loop().time() - start_time if asyncio.get_event_loop().is_running() else 60
                                    speed = (completed / elapsed_time) * 60  # Hoteles por minuto
                                    speed_metric.empty()
                                    speed_metric.metric("⚡ Velocidad", f"{speed:.1f} hoteles/min")
                                
                                # Actualizar barra de progreso
                                progress = completed / total if total > 0 else 0
                                progress_bar.progress(progress)
                                
                                # Mostrar hoteles activos con su posición
                                active_hotels_container.empty()
                                if active_urls:
                                    # Crear un mapeo de URL a posición en la lista original
                                    url_to_position = {url: i + 1 for i, url in enumerate(hotel_urls)}
                                    
                                    # Ordenar las URLs activas por su posición original
                                    sorted_active_urls = sorted(active_urls, key=lambda url: url_to_position.get(url, 999))
                                    
                                    # Mostrar cada hotel activo con su información
                                    hotels_display = ""
                                    for url in sorted_active_urls[:search_params.get('max_concurrent', 5)]:
                                        position = url_to_position.get(url, 0)
                                        hotel_name = self.booking_service._extract_hotel_name_from_url(url)
                                        hotels_display += f"**{position}/{total}** - 🏨 `{hotel_name}`\n\n"
                                    
                                    active_hotels_container.markdown(hotels_display)
                                else:
                                    if completed >= total:
                                        active_hotels_container.success("✅ ¡Todos los hoteles han sido procesados!")
                                    else:
                                        active_hotels_container.info("⏳ Preparando siguiente lote...")
                                        
                            except Exception as e:
                                logger.error(f"Error actualizando progreso de extracción: {e}")
                        
                        # Crear contexto de búsqueda con la información de cada hotel
                        search_context = {}
                        for i, hotel in enumerate(hotels):
                            base_url = hotel.get('url', '').split('?')[0]
                            if base_url:
                                # Añadir posición en los resultados
                                hotel_context = hotel.copy()
                                hotel_context['posicion'] = i + 1
                                search_context[base_url] = hotel_context
                        
                        extracted_results = loop.run_until_complete(
                            self.booking_service.scrape_hotels(
                                hotel_urls, 
                                progress_callback=extraction_progress, 
                                max_images=search_params.get('max_images', 10),
                                search_context=search_context,
                                max_concurrent=search_params.get('max_concurrent', 5)
                            )
                        )
                        successful_hotels = [r for r in extracted_results if not r.get("error")]
                        
                        if successful_hotels:
                            # COMENTADO: Ya no guardamos automáticamente en MongoDB
                            # progress_container.info("💾 Guardando datos en MongoDB...")
                            # ... código de MongoDB comentado ...
                            
                            # Enviar directamente los datos completos a n8n
                            progress_container.info("📤 Enviando datos a n8n...")
                            n8n_notification_result = self.booking_service.notify_n8n_webhook(successful_hotels)
                            if n8n_notification_result.get("success"):
                                Alert.success(n8n_notification_result.get("message"))
                            else:
                                Alert.error(n8n_notification_result.get("message", "Error desconocido al notificar a n8n."))
                            
                            st.session_state.booking_search_results = extracted_results
                            st.session_state.show_mongo_success = False
                        else:
                            Alert.warning("No se pudieron extraer datos de ningún hotel")
                            st.session_state.booking_search_results = search_results
                    else:
                        Alert.warning("No se encontraron URLs válidas para extraer")
                        st.session_state.booking_search_results = search_results
                else: # Checkbox desmarcado
                    if not st.session_state.get("proyecto_nombre"):
                        Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
                        st.session_state.booking_search_results = search_results
                        progress_container.empty()
                        st.rerun()
                        return
                    
                    proyecto_activo = st.session_state.proyecto_nombre
                    from config.settings import normalize_project_name, get_collection_name
                    proyecto_normalizado = normalize_project_name(proyecto_activo)
                    collection_name = get_collection_name(proyecto_activo, "buscar_hoteles_booking")
                    
                    import copy
                    from datetime import datetime
                    search_results_with_metadata = copy.deepcopy(search_results)
                    timestamp = datetime.now().isoformat()
                    search_results_with_metadata["_guardado_automatico"] = timestamp
                    search_results_with_metadata["_proyecto_activo"] = proyecto_activo
                    search_results_with_metadata["_proyecto_normalizado"] = proyecto_normalizado
                    
                    mongo_id = self.get_mongo_repo().insert_one(search_results_with_metadata, collection_name=collection_name)
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
        results = st.session_state.booking_search_results
        if not results: return
        
        common_mongo_message = ""
        if st.session_state.get('show_mongo_success', False) and st.session_state.get('last_mongo_id'):
            common_mongo_message = f"✅ Datos guardados en MongoDB: {st.session_state.last_mongo_id}"

        hotel_details_list_content = st.session_state.get('hotel_details_list')

        if isinstance(results, list):
            st.subheader("📊 Resultados de extracción de datos")
            if common_mongo_message: st.success(common_mongo_message)
            if hotel_details_list_content:
                with st.expander("📋 Ver detalles de hoteles guardados", expanded=False):
                    for hotel_detail in hotel_details_list_content: st.write(hotel_detail)
            
            successful = [r for r in results if not r.get("error")]
            failed = [r for r in results if r.get("error")]
            total_images = sum(len(r.get("meta", {}).get("images", [])) for r in successful)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total procesados", len(results))
            with col2: st.metric("Exitosos", len(successful))
            with col3: st.metric("Con errores", len(failed))
            with col4: st.metric("Imágenes extraídas", total_images)
            
            self._render_export_options()
            self._display_extracted_hotels(results)

        elif isinstance(results, dict):
            st.subheader("📊 Resultados de la búsqueda")
            if common_mongo_message: st.success(common_mongo_message)
            if hotel_details_list_content:
                with st.expander("📋 Ver detalles de hoteles guardados", expanded=False):
                    for hotel_detail in hotel_details_list_content: st.write(hotel_detail)

            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Hoteles encontrados", len(results.get("hotels", [])))
            with col2: st.metric("Parámetros de búsqueda", len(results.get("search_params", {})))
            with col3:
                if results.get("fecha_busqueda"):
                    fecha = datetime.fromisoformat(results["fecha_busqueda"].replace('Z', '+00:00'))
                    st.metric("Búsqueda realizada", fecha.strftime("%H:%M:%S"))

            with st.expander("🔗 URL de búsqueda utilizada"):
                st.markdown("**URL inicial:**"); st.code(results.get("search_url", ""), language="text")
                if results.get("search_params", {}).get("natural_language_filter"):
                    if results.get("filtered_url"):
                        st.markdown("**URL después de aplicar filtros inteligentes:**"); st.code(results.get("filtered_url", ""), language="text")
                        st.caption(f"✅ Filtro aplicado correctamente: '{results.get('search_params', {}).get('natural_language_filter')}'")
                    elif results.get("filter_warning"):
                        st.warning(f"⚠️ {results.get('filter_warning')}")
                        st.caption(f"Filtro intentado: '{results.get('search_params', {}).get('natural_language_filter')}'")
            
            self._render_export_options()
            self._display_hotels(results.get("hotels", []))
        else:
            st.warning(f"Formato de resultados inesperado: {type(results)}")
    
    def _render_export_options(self):
        st.session_state.booking_search_export_filename = st.text_input("📄 Nombre del archivo para exportar:", value=st.session_state.booking_search_export_filename)
        col1, col2 = st.columns(2)
        with col1: self._render_download_button()
        with col2: self._render_drive_upload_button()
    
    def _render_download_button(self):
        results = st.session_state.booking_search_results
        results_for_json = self._prepare_results_for_json(results)
        json_bytes = json.dumps(results_for_json, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(label="⬇️ Descargar JSON", data=json_bytes, file_name=st.session_state.booking_search_export_filename, mime="application/json")
    
    def _render_drive_upload_button(self):
        if Button.secondary("Subir a Drive", icon="☁️"):
            if "proyecto_id" not in st.session_state:
                Alert.warning("Selecciona un proyecto en la barra lateral"); return
            try:
                results = st.session_state.booking_search_results
                results_for_json = self._prepare_results_for_json(results)
                json_bytes = json.dumps(results_for_json, ensure_ascii=False, indent=2).encode("utf-8")
                folder_id = self.drive_service.get_or_create_folder("busquedas booking", st.session_state.proyecto_id)
                link = self.drive_service.upload_file(st.session_state.booking_search_export_filename, json_bytes, folder_id)
                if link: Alert.success(f"Archivo subido: [Ver en Drive]({link})")
                else: Alert.error("Error al subir archivo")
            except Exception as e: Alert.error(f"Error al subir a Drive: {str(e)}")
    
    def _display_hotels(self, hotels: List[Dict[str, Any]]):
        if not hotels: st.info("No se encontraron hoteles"); return
        st.subheader(f"🏨 Hoteles encontrados ({len(hotels)})")
        DataDisplay.json(self._prepare_results_for_json(st.session_state.booking_search_results), title="JSON Completo de la Búsqueda", expanded=True)
    
    def _display_extracted_hotels(self, extracted_data: List[Dict[str, Any]]):
        if not extracted_data: st.info("No se extrajeron datos"); return
        json_export = self._prepare_results_for_extraction_json(extracted_data)
        DataDisplay.json(json_export, title="JSON Completo (estructura exportación)", expanded=True)
    
    def _prepare_results_for_extraction_json(self, data):
        if isinstance(data, list):
            # Convertir lista a diccionario con claves "post-X"
            result_dict = {}
            for i, item in enumerate(data):
                result_dict[f"post-{i}"] = self._prepare_results_for_extraction_json(item)
            return result_dict
        elif isinstance(data, dict): 
            return {k: self._prepare_results_for_extraction_json(v) for k, v in data.items()}
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId': 
            return str(data)
        else: 
            return data
    
    def _prepare_results_for_json(self, data):
        if isinstance(data, dict): 
            return {k: self._prepare_results_for_json(v) for k, v in data.items() if k not in ["_id", "mongo_id"]}
        elif isinstance(data, list): 
            # Convertir lista a diccionario con claves "post-X"
            result_dict = {}
            for i, item in enumerate(data):
                result_dict[f"post-{i}"] = self._prepare_results_for_json(item)
            return result_dict
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId': 
            return str(data)
        else: 
            return data
