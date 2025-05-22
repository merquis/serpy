"""
Página de UI para Scraping de Booking.com
"""
import streamlit as st
import asyncio
import json
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.booking_scraping_service import BookingScrapingService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
from config import config

class BookingScrapingPage:
    """Página para extraer datos de hoteles de Booking.com"""
    
    def __init__(self):
        self.booking_service = BookingScrapingService()
        self.drive_service = DriveService()
        self.mongo_repo = MongoRepository(
            uri=st.secrets["mongodb"]["uri"],
            db_name=st.secrets["mongodb"]["db"]
        )
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "booking_urls_input" not in st.session_state:
            st.session_state.booking_urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?checkin=2025-07-10&checkout=2025-07-15&group_adults=2&group_children=0&no_rooms=1&dest_type=hotel"
        if "booking_results" not in st.session_state:
            st.session_state.booking_results = []
        if "booking_export_filename" not in st.session_state:
            st.session_state.booking_export_filename = "hoteles_booking.json"
    
    def render(self):
        """Renderiza la página completa"""
        st.title("🏨 Scraping de Booking.com")
        st.markdown("### 🔍 Extrae información detallada de hoteles desde sus URLs")
        
        # Área de entrada de URLs
        self._render_url_input()
        
        # Botón de scraping
        self._render_scraping_section()
        
        # Mostrar resultados si existen
        if st.session_state.booking_results:
            self._render_results_section()
    
    def _render_url_input(self):
        """Renderiza el área de entrada de URLs"""
        st.session_state.booking_urls_input = st.text_area(
            "📝 Pega URLs de hoteles de Booking (una por línea):",
            value=st.session_state.booking_urls_input,
            height=150,
            help="Asegúrate de que las URLs sean de páginas de hoteles específicos en Booking.com"
        )
        
        # Mostrar estadísticas de URLs
        urls = self._parse_urls(st.session_state.booking_urls_input)
        if urls:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("URLs válidas", len(urls))
            with col2:
                st.metric("URLs de Booking", len([u for u in urls if "booking.com/hotel/" in u]))
            with col3:
                st.metric("Otras URLs", len([u for u in urls if "booking.com/hotel/" not in u]))
    
    def _render_scraping_section(self):
        """Renderiza la sección de scraping"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if Button.primary("Scrapear Hoteles", icon="🔍"):
                self._perform_scraping()
        
        with col2:
            if st.session_state.booking_results:
                if Button.secondary("Limpiar", icon="🧹"):
                    self._clear_results()
    
    def _perform_scraping(self):
        """Ejecuta el scraping de las URLs"""
        urls = self._parse_urls(st.session_state.booking_urls_input)
        booking_urls = [url for url in urls if "booking.com/hotel/" in url]
        
        if not booking_urls:
            Alert.warning("No se encontraron URLs válidas de Booking.com")
            return
        
        # Contenedor de progreso
        progress_container = st.empty()
        
        def update_progress(message: str):
            progress_container.info(message)
        
        with LoadingSpinner.show(f"Procesando {len(booking_urls)} hoteles..."):
            try:
                # Ejecutar scraping asíncrono
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                results = loop.run_until_complete(
                    self.booking_service.scrape_hotels(
                        booking_urls,
                        progress_callback=update_progress
                    )
                )
                
                st.session_state.booking_results = results
                
                # Contar éxitos y errores
                successful = len([r for r in results if not r.get("error")])
                failed = len([r for r in results if r.get("error")])
                
                if successful > 0:
                    Alert.success(f"✅ {successful} hoteles procesados exitosamente")
                if failed > 0:
                    Alert.warning(f"⚠️ {failed} hoteles con errores")
                
                progress_container.empty()
                st.rerun()
                
            except Exception as e:
                Alert.error(f"Error durante el scraping: {str(e)}")
            finally:
                loop.close()
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        results = st.session_state.booking_results
        
        # Resumen de resultados
        self._render_results_summary(results)
        
        # Opciones de exportación
        self._render_export_options()
        
        # Mostrar resultados detallados
        self._display_detailed_results(results)
    
    def _render_results_summary(self, results: List[Dict[str, Any]]):
        """Muestra un resumen de los resultados"""
        successful = [r for r in results if not r.get("error")]
        failed = [r for r in results if r.get("error")]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total procesados", len(results))
        with col2:
            st.metric("Exitosos", len(successful))
        with col3:
            st.metric("Con errores", len(failed))
        with col4:
            total_images = sum(len(r.get("imagenes", [])) for r in successful)
            st.metric("Imágenes extraídas", total_images)
    
    def _render_export_options(self):
        """Renderiza las opciones de exportación"""
        st.session_state.booking_export_filename = st.text_input(
            "📄 Nombre del archivo para exportar:",
            value=st.session_state.booking_export_filename
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            self._render_download_button()
        
        with col2:
            self._render_drive_upload_button()
        
        with col3:
            self._render_mongodb_upload_button()
    
    def _render_download_button(self):
        """Renderiza el botón de descarga"""
        # Convertir ObjectIds a strings antes de serializar
        results_for_json = self._prepare_results_for_json(st.session_state.booking_results)
        
        json_bytes = json.dumps(
            results_for_json,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")
        
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name=st.session_state.booking_export_filename,
            mime="application/json"
        )
    
    def _render_drive_upload_button(self):
        """Renderiza el botón de subida a Drive"""
        if Button.secondary("Subir a Drive", icon="☁️"):
            if "proyecto_id" not in st.session_state:
                Alert.warning("Selecciona un proyecto en la barra lateral")
                return
            
            try:
                # Convertir a JSON
                results_for_json = self._prepare_results_for_json(st.session_state.booking_results)
                json_bytes = json.dumps(
                    results_for_json,
                    ensure_ascii=False,
                    indent=2
                ).encode("utf-8")
                
                # Obtener carpeta
                folder_id = self.drive_service.get_or_create_folder(
                    "scraping booking",
                    st.session_state.proyecto_id
                )
                
                # Subir archivo
                link = self.drive_service.upload_file(
                    st.session_state.booking_export_filename,
                    json_bytes,
                    folder_id
                )
                
                if link:
                    Alert.success(f"Archivo subido: [Ver en Drive]({link})")
                else:
                    Alert.error("Error al subir archivo")
                    
            except Exception as e:
                Alert.error(f"Error al subir a Drive: {str(e)}")
    
    def _render_mongodb_upload_button(self):
        """Renderiza el botón de subida a MongoDB"""
        if Button.secondary("Subir a MongoDB", icon="📤"):
            try:
                # Solo subir hoteles exitosos
                successful_hotels = [r for r in st.session_state.booking_results if not r.get("error")]
                
                if not successful_hotels:
                    Alert.warning("No hay hoteles exitosos para subir")
                    return
                
                # Insertar en MongoDB
                if len(successful_hotels) > 1:
                    inserted_ids = self.mongo_repo.insert_many(
                        successful_hotels,
                        collection_name="hoteles"
                    )
                    Alert.success(f"✅ {len(inserted_ids)} hoteles subidos a MongoDB")
                else:
                    inserted_id = self.mongo_repo.insert_one(
                        successful_hotels[0],
                        collection_name="hoteles"
                    )
                    Alert.success(f"✅ Hotel subido a MongoDB con ID: `{inserted_id}`")
                    
            except Exception as e:
                Alert.error(f"Error al subir a MongoDB: {str(e)}")
    
    def _display_detailed_results(self, results: List[Dict[str, Any]]):
        """Muestra los resultados detallados"""
        st.subheader("📊 Resultados detallados")
        
        # Tabs para exitosos y fallidos
        tab1, tab2 = st.tabs(["✅ Exitosos", "❌ Con errores"])
        
        with tab1:
            successful = [r for r in results if not r.get("error")]
            if successful:
                for hotel in successful:
                    self._display_hotel_card(hotel)
            else:
                st.info("No hay resultados exitosos")
        
        with tab2:
            failed = [r for r in results if r.get("error")]
            if failed:
                for error in failed:
                    self._display_error_card(error)
            else:
                st.info("No hay errores")
        
        # Mostrar JSON completo
        DataDisplay.json(
            results,
            title="JSON Completo",
            expanded=False
        )
    
    def _display_hotel_card(self, hotel: Dict[str, Any]):
        """Muestra una tarjeta con información del hotel"""
        with Card.create():
            # Título y valoración
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"### {hotel.get('nombre_alojamiento', 'Sin nombre')}")
                st.markdown(f"📍 {hotel.get('ciudad', '')}, {hotel.get('pais', '')}")
            with col2:
                valoracion = hotel.get('valoracion_global')
                if valoracion:
                    st.metric("Valoración", f"{valoracion}/10")
                    st.caption(f"{hotel.get('numero_opiniones', 0)} opiniones")
            
            # Información básica
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Tipo:** {hotel.get('tipo_alojamiento', 'Hotel')}")
            with col2:
                st.write(f"**Check-in:** {hotel.get('busqueda_checkin', 'N/A')}")
            with col3:
                st.write(f"**Check-out:** {hotel.get('busqueda_checkout', 'N/A')}")
            
            # Descripción
            descripcion = hotel.get('descripcion_corta')
            if descripcion:
                st.write("**Descripción:**")
                st.write(descripcion)
            
            # Servicios
            servicios = hotel.get('servicios_principales', [])
            if servicios:
                with st.expander(f"🛎️ Servicios ({len(servicios)})"):
                    # Mostrar servicios en columnas
                    cols = st.columns(3)
                    for i, servicio in enumerate(servicios):
                        cols[i % 3].write(f"• {servicio}")
            
            # Imágenes
            imagenes = hotel.get('imagenes', [])
            if imagenes:
                with st.expander(f"🖼️ Imágenes ({len(imagenes)})"):
                    # Mostrar primera imagen
                    if len(imagenes) > 0:
                        st.image(imagenes[0], caption="Imagen principal")
                    
                    # Enlaces a todas las imágenes
                    st.write("**Todas las imágenes:**")
                    for i, img_url in enumerate(imagenes):
                        st.code(img_url)
            
            # URL original
            st.caption(f"🔗 [Ver en Booking]({hotel.get('url_original', '')})")
    
    def _display_error_card(self, error: Dict[str, Any]):
        """Muestra una tarjeta de error"""
        with Card.create():
            st.markdown(f"### ❌ Error: {error.get('error', 'Error desconocido')}")
            st.write(f"**URL:** {error.get('url_original', 'N/A')}")
            
            details = error.get('details')
            if details:
                st.write(f"**Detalles:** {details}")
    
    def _parse_urls(self, text: str) -> List[str]:
        """Parsea las URLs del texto de entrada"""
        lines = text.strip().split('\n')
        urls = []
        
        for line in lines:
            line = line.strip()
            if line and line.startswith('http'):
                urls.append(line)
        
        return urls
    
    def _prepare_results_for_json(self, data):
        """Prepara los resultados para serialización JSON"""
        if isinstance(data, dict):
            return {k: self._prepare_results_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._prepare_results_for_json(item) for item in data]
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId':
            return str(data)
        else:
            return data
    
    def _clear_results(self):
        """Limpia los resultados"""
        st.session_state.booking_results = []
        st.rerun() 