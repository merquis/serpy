"""Página de UI para Búsqueda en Booking.com""" 
import streamlit as st
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from bs4 import BeautifulSoup
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
            params['destination'] = st.text_area(
                "📍 Destino(s)", value="", placeholder="Escribe uno o más destinos, separados por saltos de línea...",
                help="Puedes introducir múltiples destinos, uno por cada línea.", key=f"destination_input_{st.session_state.form_reset_count}",
                height=180
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
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
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
            params['search_concurrent'] = st.number_input("� Búsquedas concurrentes", min_value=1, max_value=10, value=3, step=1, help="Número de búsquedas de destinos a ejecutar en paralelo.", key=f"search_concurrent_input_{st.session_state.form_reset_count}")
        with col6:
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
        
        destinations_text = search_params.get('destination', '')
        destinations = [dest.strip() for dest in destinations_text.split('\n') if dest.strip()]

        if not destinations:
            Alert.warning("Por favor, introduce al menos un destino.")
            return

        def update_progress(info: Dict[str, Any]):
            progress_container.info(info.get("message", "Procesando..."))

        extract_data = search_params.get('extract_hotel_data', False)
        
        all_hotels = []
        all_extracted_results = []
        
        with st.container(): # Usar un contenedor para todo el proceso
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Si vamos a extraer datos, usar pipeline optimizado
                if extract_data:
                    # Pipeline optimizado: búsqueda y extracción en paralelo
                    results = loop.run_until_complete(
                        self._perform_pipeline_search_and_extract(
                            destinations, 
                            search_params, 
                            progress_container
                        )
                    )
                    all_hotels = results['all_hotels']
                    all_extracted_results = results['extracted_results']
                    
                else:
                    # Modo solo búsqueda (sin extracción)
                    concurrency = search_params.get('search_concurrent', 3)
                    semaphore = asyncio.Semaphore(concurrency)
                    
                    # --- Contenedores para el progreso de búsqueda de destinos ---
                    st.info(f"🔍 Buscando URLs en {len(destinations)} destinos con {concurrency} búsquedas concurrentes")
                    col1, col2 = st.columns(2)
                    completed_searches_metric = col1.empty()
                    active_searches_metric = col2.empty()
                    progress_bar_searches = st.progress(0)
                    st.markdown("---")
                    st.markdown("### 🌍 Destinos procesándose actualmente:")
                    active_searches_container = st.empty()
                    # --- Fin de contenedores ---

                    completed_count = 0
                    active_searches = set()

                    def search_progress_callback():
                        # Actualizar métricas
                        completed_searches_metric.metric("✅ Búsquedas completadas", f"{completed_count}/{len(destinations)}")
                        active_searches_metric.metric("🔄 Búsquedas activas", len(active_searches))
                        
                        # Actualizar barra de progreso
                        progress_bar_searches.progress(completed_count / len(destinations))
                        
                        # Mostrar destinos activos
                        if active_searches:
                            active_searches_container.markdown("\n".join(f"- `{dest}`" for dest in sorted(list(active_searches))))
                        else:
                            active_searches_container.empty()

                    from rebrowser_playwright.async_api import async_playwright
                    
                    async def main_search_logic():
                        async with async_playwright() as p:
                            browser = await p.chromium.launch(
                                headless=True,
                                args=[
                                    "--no-sandbox",
                                    "--disable-setuid-sandbox",
                                    "--disable-blink-features=AutomationControlled",
                                    "--disable-features=IsolateOrigins,site-per-process"
                                ]
                            )
                            try:
                                async def worker(destination_param):
                                    nonlocal completed_count
                                    try:
                                        async with semaphore:
                                            active_searches.add(destination_param)
                                            search_progress_callback()
                                            
                                            current_search_params = search_params.copy()
                                            current_search_params['destination'] = destination_param
                                            return await self.search_service.search_hotels(
                                                current_search_params,
                                                browser=browser,  # Reutilizar la instancia del navegador
                                                max_results=search_params.get('max_results', 15),
                                                progress_callback=None,
                                                mongo_repo=None
                                            )
                                    finally:
                                        completed_count += 1
                                        active_searches.discard(destination_param)
                                        search_progress_callback()

                                tasks = [worker(dest) for dest in destinations]
                                return await asyncio.gather(*tasks)
                            finally:
                                await browser.close()

                    all_search_results = loop.run_until_complete(main_search_logic())
                    
                    progress_container.info("Consolidando resultados...")

                    # Procesar los resultados
                    for i, search_result_item in enumerate(all_search_results):
                        destination = destinations[i]
                        if search_result_item.get("error"):
                            Alert.error(f"Error en la búsqueda para '{destination}': {search_result_item['error']}")
                            continue
                        
                        found_hotels = search_result_item.get("hotels", [])
                        if found_hotels:
                            all_hotels.extend(found_hotels)

                # Procesar resultados finales
                if not all_hotels:
                    Alert.warning("No se encontraron hoteles en ninguna de las búsquedas.")
                    progress_container.empty()
                    return

                # Construir resultado final
                final_results = {
                    "hotels": all_hotels,
                    "total_found": len(all_hotels),
                    "extracted": len(all_hotels),
                    "search_params": search_params,
                    "fecha_busqueda": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                
                if extract_data and all_extracted_results:
                    # Si se extrajeron datos, usar esos resultados
                    st.session_state.booking_search_results = all_extracted_results
                    
                    # Enviar a n8n si hay resultados exitosos
                    successful_hotels = [r for r in all_extracted_results if not r.get("error")]
                    if successful_hotels:
                        progress_container.info("📤 Enviando datos a n8n...")
                        n8n_notification_result = self.booking_service.notify_n8n_webhook(successful_hotels)
                        if n8n_notification_result.get("success"):
                            Alert.success(n8n_notification_result.get("message"))
                        else:
                            Alert.error(n8n_notification_result.get("message", "Error desconocido al notificar a n8n."))
                else:
                    # Modo solo búsqueda
                    st.session_state.booking_search_results = final_results
                    
                    # Guardar en MongoDB si es necesario
                    if not st.session_state.get("proyecto_nombre"):
                        Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
                    else:
                        proyecto_activo = st.session_state.proyecto_nombre
                        from config.settings import normalize_project_name, get_collection_name
                        proyecto_normalizado = normalize_project_name(proyecto_activo)
                        collection_name = get_collection_name(proyecto_activo, "buscar_hoteles_booking")
                        
                        import copy
                        from datetime import datetime
                        search_results_with_metadata = copy.deepcopy(final_results)
                        timestamp = datetime.now().isoformat()
                        search_results_with_metadata["_guardado_automatico"] = timestamp
                        search_results_with_metadata["_proyecto_activo"] = proyecto_activo
                        search_results_with_metadata["_proyecto_normalizado"] = proyecto_normalizado
                        
                        mongo_id = self.get_mongo_repo().insert_one(search_results_with_metadata, collection_name=collection_name)
                        final_results["mongo_id"] = mongo_id
                        st.session_state.booking_search_results = final_results
                        st.session_state.last_mongo_id = f"Guardado en {collection_name} con ID: {str(mongo_id)}"
                        st.session_state.show_mongo_success = True
                
                progress_container.empty()
                st.rerun()
                
            except Exception as e:
                Alert.error(f"Error durante la búsqueda: {str(e)}")
            finally:
                loop.close()
    
    async def _perform_pipeline_search_and_extract(self, destinations: List[str], search_params: Dict[str, Any], progress_container) -> Dict[str, Any]:
        """Realiza búsqueda y extracción en pipeline optimizado"""
        from rebrowser_playwright.async_api import async_playwright
        
        # Configuración de concurrencia
        search_concurrent = search_params.get('search_concurrent', 3)
        extract_concurrent = search_params.get('max_concurrent', 5)
        
        # Semáforo para limitar búsquedas concurrentes
        search_semaphore = asyncio.Semaphore(search_concurrent)
        
        # Límite global de tareas del navegador
        global_browser_limit = max(search_concurrent + extract_concurrent, 8)
        global_semaphore = asyncio.Semaphore(global_browser_limit)
        
        # Resultados
        all_hotels = []
        all_extracted_results = []
        
        # Contadores
        search_completed = 0
        extract_completed = 0
        total_hotels_to_extract = 0
        
        # Conjuntos para tracking
        active_searches = set()
        active_extractions = {}  # Cambiar a diccionario para agrupar por destino
        
        # UI containers
        progress_container.empty()
        main_container = st.container()
        
        with main_container:
            st.info(f"🚀 Modo Pipeline: Búsqueda y extracción en paralelo")
            
            # Métricas principales
            col1, col2, col3 = st.columns(3)
            with col1:
                search_metric = st.empty()
                search_metric.metric("🔍 Búsquedas", f"0/{len(destinations)}")
            with col2:
                extract_metric = st.empty()
                extract_metric.metric("📊 Extracciones", "0/0")
            with col3:
                active_metric = st.empty()
                active_metric.metric("⚡ Tareas activas", "0")
            
            # Barra de progreso global
            progress_bar = st.progress(0)
            
            # Contenedores de estado
            st.markdown("---")
            active_searches_container = st.empty()
            active_extractions_container = st.empty()
        
        def update_ui():
            """Actualiza la interfaz con el estado actual"""
            # Actualizar métricas
            search_metric.metric("🔍 Búsquedas", f"{search_completed}/{len(destinations)}")
            extract_metric.metric("📊 Extracciones", f"{extract_completed}/{total_hotels_to_extract}")
            active_metric.metric("⚡ Tareas activas", len(active_searches) + len(active_extractions))
            
            # Calcular progreso global
            total_tasks = len(destinations) + total_hotels_to_extract
            completed_tasks = search_completed + extract_completed
            if total_tasks > 0:
                progress = completed_tasks / total_tasks
                progress_bar.progress(progress)
            
            # Mostrar búsquedas activas
            if active_searches:
                searches_text = "### 🔍 Búsquedas en curso:\n"
                for dest in sorted(active_searches):
                    searches_text += f"- 🌍 **{dest}**\n"
                active_searches_container.markdown(searches_text)
            else:
                active_searches_container.empty()
            
            # Mostrar extracciones activas agrupadas por destino
            if active_extractions:
                extractions_text = "### 📊 Extrayendo datos de hoteles:\n"
                
                # Agrupar por destino y mostrar
                for destination, hotels in sorted(active_extractions.items()):
                    if hotels:  # Solo mostrar destinos con hoteles activos
                        extractions_text += f"\n**{destination}:**\n"
                        # Mostrar máximo 3 hoteles por destino
                        for hotel in list(hotels)[:3]:
                            extractions_text += f"- 🏨 {hotel}\n"
                        if len(hotels) > 3:
                            extractions_text += f"- ... y {len(hotels) - 3} más\n"
                
                active_extractions_container.markdown(extractions_text)
            else:
                active_extractions_container.empty()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            try:
                # Cola para URLs pendientes de extracción
                extraction_queue = asyncio.Queue()
                
                async def search_worker(destination: str):
                    """Worker para búsqueda de un destino"""
                    nonlocal search_completed, total_hotels_to_extract
                    
                    # Esperar turno según el límite de búsquedas concurrentes
                    async with search_semaphore:
                        async with global_semaphore:
                            try:
                                active_searches.add(destination)
                                update_ui()
                                
                                # Realizar búsqueda
                                current_search_params = search_params.copy()
                                current_search_params['destination'] = destination
                                
                                result = await self.search_service.search_hotels(
                                    current_search_params,
                                    browser=browser,
                                    max_results=search_params.get('max_results', 15),
                                    progress_callback=None,
                                    mongo_repo=None
                                )
                                
                                # Procesar resultados
                                if not result.get("error"):
                                    hotels = result.get("hotels", [])
                                    if hotels:
                                        all_hotels.extend(hotels)
                                        total_hotels_to_extract += len(hotels)
                                        
                                        # Añadir URLs a la cola de extracción
                                        for i, hotel in enumerate(hotels):
                                            url = hotel.get('url_arg', hotel.get('url', ''))
                                            if url:
                                                # Crear contexto para el hotel
                                                hotel_context = hotel.copy()
                                                hotel_context['posicion'] = len(all_hotels) - len(hotels) + i + 1
                                                hotel_context['search_term'] = destination
                                                
                                                await extraction_queue.put({
                                                    'url': url,
                                                    'context': hotel_context,
                                                    'destination': destination
                                                })
                                else:
                                    Alert.error(f"Error en búsqueda '{destination}': {result['error']}")
                                
                            finally:
                                search_completed += 1
                                active_searches.discard(destination)
                                update_ui()
                
                async def extraction_worker():
                    """Worker para extracción de datos de hoteles"""
                    nonlocal extract_completed
                    
                    while True:
                        try:
                            # Si todas las búsquedas terminaron Y la cola está vacía, salir
                            if search_completed >= len(destinations) and extraction_queue.empty():
                                await asyncio.sleep(0.5)  # Pequeña espera final para asegurar
                                if extraction_queue.empty():  # Doble verificación
                                    break
                            
                            # Esperar por trabajo con timeout más largo
                            hotel_data = await asyncio.wait_for(extraction_queue.get(), timeout=5.0)
                            
                            async with global_semaphore:
                                url = hotel_data['url']
                                context = hotel_data['context']
                                hotel_name = self.booking_service._extract_hotel_name_from_url(url)
                                
                                try:
                                    # Añadir hotel al destino correspondiente
                                    destination = hotel_data['destination']
                                    if destination not in active_extractions:
                                        active_extractions[destination] = set()
                                    active_extractions[destination].add(hotel_name)
                                    update_ui()
                                    
                                    # Crear página para extracción
                                    page = await browser.new_page(viewport={"width": 1920, "height": 1080})
                                    
                                    try:
                                        # Navegar y extraer datos
                                        await page.goto(url, wait_until="networkidle", timeout=60000)
                                        await page.wait_for_timeout(2000)
                                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                                        await page.wait_for_timeout(1500)
                                        
                                        html_content = await page.content()
                                        js_data = await self.booking_service._extract_javascript_data(page)
                                        
                                        soup = BeautifulSoup(html_content, "html.parser")
                                        hotel_result = self.booking_service._parse_hotel_html(
                                            soup, url, js_data, 
                                            search_params.get('max_images', 10),
                                            context
                                        )
                                        
                                        all_extracted_results.append(hotel_result)
                                        
                                    finally:
                                        await page.close()
                                    
                                except Exception as e:
                                    logger.error(f"Error extrayendo {url}: {e}")
                                    error_result = self.booking_service._generate_error_response(url, str(e))
                                    all_extracted_results.append(error_result)
                                
                                finally:
                                    extract_completed += 1
                                    # Eliminar hotel del destino correspondiente
                                    destination = hotel_data['destination']
                                    if destination in active_extractions:
                                        active_extractions[destination].discard(hotel_name)
                                        # Si no quedan hoteles en ese destino, eliminar el destino
                                        if not active_extractions[destination]:
                                            del active_extractions[destination]
                                    update_ui()
                        
                        except asyncio.TimeoutError:
                            # Si hay timeout pero las búsquedas no han terminado, continuar esperando
                            if search_completed < len(destinations):
                                continue
                            else:
                                # Si las búsquedas terminaron y hay timeout, verificar cola una vez más
                                if extraction_queue.empty():
                                    break
                                else:
                                    continue
                        except Exception as e:
                            logger.error(f"Error en extraction worker: {e}")
                            continue
                
                # Iniciar tareas de búsqueda
                search_tasks = [search_worker(dest) for dest in destinations]
                
                # Iniciar workers de extracción
                num_extraction_workers = min(extract_concurrent, 5)
                extraction_tasks = [extraction_worker() for _ in range(num_extraction_workers)]
                
                logger.info(f"Iniciando pipeline con {len(search_tasks)} búsquedas y {num_extraction_workers} workers de extracción")
                
                # Ejecutar todo en paralelo
                await asyncio.gather(
                    *search_tasks,
                    *extraction_tasks,
                    return_exceptions=True
                )
                
                # Asegurar que todas las extracciones pendientes se completen
                while not extraction_queue.empty():
                    await asyncio.sleep(0.1)
                    update_ui()
                
                # Esperar un poco más para asegurar que los workers terminen
                await asyncio.sleep(1)
                
                logger.info(f"Pipeline completado: {search_completed} búsquedas, {extract_completed} extracciones")
                
            finally:
                await browser.close()
        
        return {
            'all_hotels': all_hotels,
            'extracted_results': all_extracted_results
        }
    
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
