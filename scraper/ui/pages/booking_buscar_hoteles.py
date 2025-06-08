


"""Página de UI para Búsqueda en Booking.com""" 
import streamlit as st
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.booking_buscar_hoteles_service import BookingBuscarHotelesService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
from config import config

class BookingBuscarHotelesPage:
    """Página para buscar hoteles en Booking.com con parámetros"""
    
    def __init__(self):
        self.search_service = BookingBuscarHotelesService()
        self.drive_service = DriveService()
        self.mongo_repo = MongoRepository(
            uri=st.secrets["mongodb"]["uri"],
            db_name=st.secrets["mongodb"]["db"]
        )
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "booking_search_results" not in st.session_state:
            st.session_state.booking_search_results = None
        if "booking_search_export_filename" not in st.session_state:
            st.session_state.booking_search_export_filename = "busqueda_booking.json"
        if "reset_form" not in st.session_state:
            st.session_state.reset_form = False
    
    def _on_checkin_change(self):
        """Callback cuando cambia la fecha de entrada"""
        # Obtener el form_reset_count actual
        form_reset_count = st.session_state.get('form_reset_count', 0)
        checkin_key = f"checkin_input_{form_reset_count}"
        checkout_key = f"checkout_input_{form_reset_count}"
        
        if checkin_key in st.session_state:
            # Actualizar la fecha de salida para ser un día después
            new_checkout = st.session_state[checkin_key] + timedelta(days=1)
            st.session_state[checkout_key] = new_checkout
            # Forzar actualización
            st.session_state['checkout_updated'] = True
    
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
                "pets_input", "max_results_input", "natural_filter_input"
            ]
            for i in range(10):
                keys_to_clear.append(f"child_age_{i}")
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.reset_form = False

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
            
            checkin_date = st.date_input(
                "📅 Fecha de entrada",
                value=datetime.now(),
                min_value=datetime.now(),
                key=checkin_key,
                on_change=self._on_checkin_change
            )
            
            params['checkin'] = checkin_date.strftime('%Y-%m-%d')
        
        with col3:
            checkout_key = f"checkout_input_{st.session_state.form_reset_count}"
            
            # Valor por defecto para checkout
            if checkout_key not in st.session_state:
                # Si es la primera vez, usar checkin + 1 día
                st.session_state[checkout_key] = checkin_date + timedelta(days=1)
            
            # Si se actualizó el checkout desde el callback, limpiar el flag
            if st.session_state.get('checkout_updated', False):
                st.session_state['checkout_updated'] = False
            
            params['checkout'] = st.date_input(
                "📅 Fecha de salida",
                value=st.session_state[checkout_key],
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

        return params
    
    def _perform_search(self, search_params: Dict[str, Any]):
        """Ejecuta la búsqueda con los parámetros especificados"""
        # Contenedor de progreso
        progress_container = st.empty()
        
        def update_progress(info: Dict[str, Any]):
            progress_container.info(info.get("message", "Procesando..."))
        
        with LoadingSpinner.show(f"Buscando hoteles en Booking..."):
            try:
                # Ejecutar búsqueda asíncrona
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                results = loop.run_until_complete(
                    self.search_service.search_hotels(
                        search_params,
                        max_results=search_params.get('max_results', 15),
                        progress_callback=update_progress
                    )
                )
                
                st.session_state.booking_search_results = results
                
                if results.get("error"):
                    Alert.error(f"Error en la búsqueda: {results['error']}")
                else:
                    hotels_found = len(results.get("hotels", []))
                    Alert.success(f"✅ Búsqueda completada: {hotels_found} hoteles encontrados")
                
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
        
        # Información de la búsqueda
        st.subheader("📊 Resultados de la búsqueda")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Hoteles encontrados", len(results.get("hotels", [])))
        with col2:
            st.metric("Parámetros de búsqueda", len(results.get("search_params", {})))
        with col3:
            if results.get("fecha_busqueda"):
                fecha = datetime.fromisoformat(results["fecha_busqueda"].replace('Z', '+00:00'))
                st.metric("Búsqueda realizada", fecha.strftime("%H:%M:%S"))
        
        # URL de búsqueda
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
        self._display_hotels(results.get("hotels", []))
    
    def _render_export_options(self):
        """Renderiza las opciones de exportación"""
        st.session_state.booking_search_export_filename = st.text_input(
            "📄 Nombre del archivo para exportar:",
            value=st.session_state.booking_search_export_filename
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            self._render_download_button()
        
        with col2:
            self._render_drive_upload_button()
        
        with col3:
            self._render_process_hotels_button()
    
    def _render_download_button(self):
        """Renderiza el botón de descarga"""
        results = st.session_state.booking_search_results
        
        json_bytes = json.dumps(
            results,
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
                json_bytes = json.dumps(
                    results,
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
    
    def _render_process_hotels_button(self):
        """Renderiza el botón para procesar hoteles con el scraper existente"""
        if Button.secondary("Procesar Hoteles", icon="🔄"):
            hotels = st.session_state.booking_search_results.get("hotels", [])
            hotel_urls = [h['url'] for h in hotels if h.get('url')]
            
            if hotel_urls:
                # Guardar las URLs en el estado para la página de scraping
                st.session_state.booking_urls_input = "\n".join(hotel_urls)
                Alert.info(f"📋 {len(hotel_urls)} URLs copiadas. Ve a 'Booking.com' para procesarlas.")
            else:
                Alert.warning("No hay URLs de hoteles para procesar")
    
    def _display_hotels(self, hotels: List[Dict[str, Any]]):
        """Muestra los hoteles encontrados"""
        if not hotels:
            st.info("No se encontraron hoteles")
            return
        
        # Solo mostrar el título con el número de hoteles
        st.subheader(f"🏨 Hoteles encontrados ({len(hotels)})")
        
        # Mostrar directamente el JSON completo expandido
        DataDisplay.json(
            st.session_state.booking_search_results,
            title="JSON Completo de la Búsqueda",
            expanded=True
        )
