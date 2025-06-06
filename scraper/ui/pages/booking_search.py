"""
Página de UI para Búsqueda en Booking.com
"""
import streamlit as st
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.booking_search_service import BookingSearchService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
from config import config

class BookingSearchPage:
    """Página para buscar hoteles en Booking.com con parámetros"""
    
    def __init__(self):
        self.search_service = BookingSearchService()
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
    
    def render(self):
        """Renderiza la página completa"""
        st.title("🔍 Búsqueda en Booking.com")
        st.markdown("### 🏨 Busca hoteles con parámetros personalizados")
        
        # Formulario de búsqueda
        search_params = self._render_search_form()
        
        # Botón de búsqueda
        if st.button("🔍 Buscar Hoteles", type="primary", use_container_width=True):
            self._perform_search(search_params)
        
        # Mostrar resultados si existen
        if st.session_state.booking_search_results:
            self._render_results_section()
    
    def _render_search_form(self) -> Dict[str, Any]:
        """Renderiza el formulario de búsqueda"""
        params = {}
        
        # Destino y fechas en la misma línea
        col1, col2, col3 = st.columns([3, 1, 1])  # 60%, 20%, 20%
        
        with col1:
            params['destination'] = st.text_input(
                "📍 Destino",
                value="Tenerife",
                help="Ciudad, región o lugar de búsqueda"
            )
        
        with col2:
            default_checkin = datetime.now()  # Fecha actual por defecto
            params['checkin'] = st.date_input(
                "📅 Fecha de entrada",
                value=default_checkin,
                min_value=datetime.now()
            ).strftime('%Y-%m-%d')
        
        with col3:
            default_checkout = default_checkin + timedelta(days=2)  # 2 días después por defecto
            params['checkout'] = st.date_input(
                "📅 Fecha de salida",
                value=default_checkout,
                min_value=datetime.now() + timedelta(days=1)
            ).strftime('%Y-%m-%d')
        
        # Ocupación
        st.subheader("👥 Ocupación")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            params['adults'] = st.number_input(
                "Adultos",
                min_value=1,
                max_value=30,
                value=2
            )
        
        with col2:
            params['children'] = st.number_input(
                "Niños",
                min_value=0,
                max_value=10,
                value=0
            )
        
        with col3:
            params['rooms'] = st.number_input(
                "Habitaciones",
                min_value=1,
                max_value=30,
                value=1
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
                        key=f"child_age_{i}"
                    )
                    children_ages.append(age)
            params['children_ages'] = children_ages
        
        # Filtros
        st.subheader("🎯 Filtros")
        
        # Filtro inteligente de lenguaje natural
        st.markdown("### 🤖 Filtros inteligentes")
        params['natural_language_filter'] = st.text_area(
            "¿Qué estás buscando?",
            placeholder="Escribe en lenguaje natural lo que buscas, por ejemplo: '1 y 2 estrellas', 'hoteles con piscina', 'cerca de la playa', etc.",
            height=80,
            help="Este texto se transferirá al filtro inteligente de Booking.com"
        )
        
        st.markdown("---")
        
        # Estrellas
        col1, col2 = st.columns(2)
        with col1:
            stars_options = st.multiselect(
                "⭐ Categoría (estrellas)",
                options=[1, 2, 3, 4, 5],
                default=[4, 5]
            )
            params['stars'] = stars_options
        
        with col2:
            params['min_score'] = st.selectbox(
                "📊 Puntuación mínima",
                options=['Sin filtro', '7.0', '8.0', '9.0'],
                index=3
            )
            if params['min_score'] == 'Sin filtro':
                params['min_score'] = None
        
        # Régimen (ahora es multiselect)
        col1, col2 = st.columns([3, 1])
        
        with col1:
            meal_plan_options = {
                'solo_alojamiento': 'Solo alojamiento',
                'desayuno': 'Desayuno incluido',
                'media_pension': 'Media pensión',
                'pension_completa': 'Pensión completa',
                'todo_incluido': 'Todo incluido',
                'desayuno_buffet': 'Desayuno buffet'
            }
            
            selected_meal_plans = st.multiselect(
                "🍽️ Régimen alimenticio",
                options=list(meal_plan_options.keys()),
                default=['todo_incluido'],  # Por defecto seleccionamos todo incluido
                format_func=lambda x: meal_plan_options[x]
            )
            
            # Solo añadir meal_plan si hay opciones seleccionadas
            if selected_meal_plans:
                params['meal_plan'] = selected_meal_plans
        
        with col2:
            # Checkbox para mascotas
            params['pets_allowed'] = st.checkbox(
                "🐾 Se admiten mascotas",
                value=False,
                help="Filtrar solo hoteles que admiten mascotas"
            )
        
        # Número de resultados
        params['max_results'] = st.slider(
            "📊 Número máximo de hoteles a extraer",
            min_value=5,
            max_value=50,
            value=15,
            step=5,
            help="Número de URLs de hoteles que se extraerán de los resultados"
        )
        
        # Mostrar URL generada
        with st.expander("🔗 Ver URL de búsqueda generada"):
            preview_url = self.search_service.build_search_url(params)
            st.code(preview_url, language="text")
            st.caption("Esta es la URL que se utilizará para la búsqueda")
        
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
