"""
Página de UI para Scraping de Booking.com
"""
import streamlit as st
import asyncio
import json
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.booking_extraer_datos_service import BookingExtraerDatosService
from services.drive_service import DriveService
from services.simple_image_download import SimpleImageDownloadService
from services.direct_image_download import DirectImageDownloadService
import requests
from repositories.mongo_repository import MongoRepository
from config import settings
import logging
import copy # Añadido para deepcopy
from datetime import datetime # Añadido para timestamp

logger = logging.getLogger(__name__)

class BookingExtraerDatosPage:
    """Página para extraer datos de hoteles de Booking.com"""
    
    def __init__(self):
        self.booking_service = BookingExtraerDatosService()
        self.drive_service = DriveService()
        self.image_download_service = SimpleImageDownloadService()
        self.direct_download_service = DirectImageDownloadService() # Instanciar una vez
        self._mongo_repo = None
        self._init_session_state()
    
    def get_mongo_repo(self):
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
        defaults = {
            "booking_urls_input": "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?checkin=2025-07-10&checkout=2025-07-15&group_adults=2&group_children=0&no_rooms=1&dest_type=hotel",
            "booking_results": [],
            "booking_export_filename": "hoteles_booking.json",
            "booking_input_mode": "URL manual",
            "selected_mongo_doc": None,
            "scraping_in_progress": False,
            "scraping_already_launched": False,
            "booking_max_concurrent": 5  # Valor por defecto para concurrencia
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def render(self):
        st.title("🏨 Scraping de Booking.com")
        st.markdown("### 🔍 Extrae información detallada de hoteles desde sus URLs")
        self._render_url_input()
        self._render_scraping_section()
        if st.session_state.booking_results:
            self._render_results_section()
    
    def _render_url_input(self):
        st.session_state.booking_input_mode = st.radio(
            "Selecciona el origen de las URLs:",
            ["URL manual", "Desde MongoDB"],
            horizontal=True,
            index=0 if st.session_state.booking_input_mode == "URL manual" else 1
        )
        
        if st.session_state.booking_input_mode == "URL manual":
            st.session_state.booking_urls_input = st.text_area(
                "📝 Pega URLs de hoteles de Booking:",
                value=st.session_state.booking_urls_input,
                height=150,
                help="""Puedes introducir:
                - URLs separadas por líneas
                - URLs separadas por comas
                - Un JSON con resultados de búsqueda (con campo 'hotels' que contenga 'url_arg')"""
            )
            urls = self.booking_service.parse_urls_input(st.session_state.booking_urls_input)
            if urls:
                col1, col2, col3 = st.columns(3)
                col1.metric("URLs válidas", len(urls))
                col2.metric("URLs de Booking", len([u for u in urls if "booking.com/hotel/" in u]))
                col3.metric("Otras URLs", len([u for u in urls if "booking.com/hotel/" not in u]))
                with st.expander("🔍 Vista previa de URLs detectadas", expanded=False):
                    for i, url in enumerate(urls):
                        st.write(f"{i+1}. {url}")
        else:
            self._render_mongodb_url_input()

    def _render_mongodb_url_input(self):
        if not st.session_state.get("proyecto_nombre"):
            Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
            return
            
        proyecto_activo = st.session_state.proyecto_nombre
        from config.settings import get_collection_name
        collection_name = get_collection_name(proyecto_activo, "buscar_hoteles_booking")
            
        try:
            documents = self.get_mongo_repo().find_many({}, collection_name=collection_name, limit=100, sort=[("_id", -1)])
            if not documents:
                st.warning(f"No se encontraron documentos en la colección '{collection_name}' para el proyecto '{proyecto_activo}'.")
                return

            options = [(f"{doc.get('search_params', {}).get('destination', 'N/D')} - {len(doc.get('hotels', []))} hoteles - ID: {str(doc.get('_id', ''))[-6:]}", doc) for doc in documents]
            selected_label, selected_doc = st.selectbox(
                "Selecciona un documento de MongoDB:", options, format_func=lambda x: x[0]
            )
            
            if selected_doc:
                st.session_state.selected_mongo_doc = selected_doc
                hotels = selected_doc.get('hotels', [])
                st.metric("Hoteles en documento", len(hotels))
                if st.button("📥 Cargar URLs desde este documento", type="secondary"):
                    st.session_state.booking_urls_input = json.dumps(selected_doc, default=str)
                    Alert.success(f"✅ Cargados {len(hotels)} hoteles desde MongoDB. Haz clic en 'Scrapear Hoteles'.")
                    st.session_state.booking_input_mode = "URL manual" # Cambiar a manual para que se procese el JSON
                    st.rerun()

        except Exception as e:
            st.error(f"Error al conectar o leer de MongoDB: {str(e)}")

    def _render_scraping_section(self):
        # Configuración de concurrencia
        st.markdown("#### ⚙️ Configuración de scraping")
        
        # Checkbox para extraer información de URLs
        extract_urls = st.checkbox("📊 Extraer información URLs", value=True)
        
        # Mostrar slider solo si el checkbox está activado
        if extract_urls:
            st.session_state.booking_max_concurrent = st.slider(
                "🔄 URLs concurrentes",
                min_value=1,
                max_value=20,
                value=st.session_state.booking_max_concurrent,
                help="Número de URLs a procesar simultáneamente. Más URLs = más rápido pero más recursos."
            )
            
            # Mostrar información sobre la concurrencia
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"🚀 Procesando {st.session_state.booking_max_concurrent} URLs a la vez")
            with col2:
                if st.session_state.booking_max_concurrent <= 5:
                    st.success("✅ Velocidad conservadora")
                elif st.session_state.booking_max_concurrent <= 10:
                    st.warning("⚡ Velocidad moderada")
                else:
                    st.error("🔥 Velocidad agresiva")
            with col3:
                urls = self.booking_service.parse_urls_input(st.session_state.booking_urls_input)
                if urls and len(urls) > 1:
                    time_estimate = len(urls) / st.session_state.booking_max_concurrent * 10  # ~10 segundos por URL
                    st.metric("⏱️ Tiempo estimado", f"{time_estimate:.0f} seg")
        
        # Botón de scraping
        col1, _ = st.columns([3, 1])
        with col1:
            if st.button("🔍 Scrapear Hoteles", type="primary", use_container_width=True, disabled=st.session_state.scraping_in_progress):
                if extract_urls:
                    st.session_state.scraping_in_progress = True
                    st.session_state.scraping_already_launched = False
                    st.rerun()
                else:
                    Alert.warning("Por favor, activa 'Extraer información URLs' para continuar")

        if st.session_state.scraping_in_progress and not st.session_state.scraping_already_launched:
            st.session_state.scraping_already_launched = True
            self._perform_scraping()
            st.session_state.scraping_in_progress = False
            st.rerun()

        if st.session_state.booking_results and not st.session_state.scraping_in_progress:
             if st.button("🧹 Limpiar Resultados", type="secondary", use_container_width=True):
                self._clear_results()
    
    def _perform_scraping(self):
        urls = self.booking_service.parse_urls_input(st.session_state.booking_urls_input)
        booking_urls = [url for url in urls if "booking.com/hotel/" in url]

        if not booking_urls:
            Alert.warning("No se encontraron URLs válidas de Booking.com para scrapear.")
            return

        # Contenedores para el progreso mejorado
        progress_container = st.container()
        
        with progress_container:
            # Métricas de progreso
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                completed_metric = st.empty()
                completed_metric.metric("✅ Completadas", "0/0")
            with col2:
                remaining_metric = st.empty()
                remaining_metric.metric("⏳ Restantes", "0")
            with col3:
                concurrent_metric = st.empty()
                concurrent_metric.metric("🔄 Concurrentes", "0")
            with col4:
                speed_metric = st.empty()
                speed_metric.metric("⚡ Velocidad", "0 URLs/min")
            
            # Barra de progreso
            progress_bar = st.progress(0)
            
            # Información de URLs activas
            st.markdown("---")
            active_urls_container = st.empty()
            active_urls_container.info("🚀 Iniciando procesamiento en paralelo...")
            
            # Tiempo de inicio para calcular velocidad
            start_time = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0

        def update_progress(info: Dict[str, Any]):
            """Actualiza la visualización del progreso"""
            try:
                completed = info.get("completed", 0)
                total = info.get("total", 1)
                remaining = info.get("remaining", 0)
                active_urls = info.get("active_urls", [])
                concurrent = info.get("concurrent", 0)
                
                # Actualizar métricas
                completed_metric.empty()
                completed_metric.metric("✅ Completadas", f"{completed}/{total}")
                
                remaining_metric.empty()
                remaining_metric.metric("⏳ Restantes", remaining)
                
                concurrent_metric.empty()
                concurrent_metric.metric("🔄 Concurrentes", concurrent)
                
                # Calcular velocidad
                if completed > 0 and start_time > 0:
                    elapsed_time = asyncio.get_event_loop().time() - start_time if asyncio.get_event_loop().is_running() else 60
                    speed = (completed / elapsed_time) * 60  # URLs por minuto
                    speed_metric.empty()
                    speed_metric.metric("⚡ Velocidad", f"{speed:.1f} URLs/min")
                
                # Actualizar barra de progreso
                progress = completed / total if total > 0 else 0
                progress_bar.progress(progress)
                
                # Mostrar URLs activas
                active_urls_container.empty()
                if active_urls:
                    urls_display = f"**🌐 Procesando {len(active_urls)} URLs simultáneamente:**\n\n"
                    for idx, url in enumerate(active_urls[:st.session_state.booking_max_concurrent]):
                        # Extraer nombre del hotel de la URL
                        hotel_name = self.booking_service._extract_hotel_name_from_url(url)
                        urls_display += f"{completed + idx + 1}. `{hotel_name}`\n"
                    active_urls_container.info(urls_display)
                else:
                    message = info.get("message", "Procesando...")
                    active_urls_container.success(message)
                    
            except Exception as e:
                logger.error(f"Error actualizando progreso: {e}")

        with LoadingSpinner.show(f"Procesando {len(booking_urls)} hoteles con {st.session_state.booking_max_concurrent} URLs concurrentes..."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Registrar tiempo de inicio
                start_time = loop.time()
                
                results = loop.run_until_complete(
                    self.booking_service.scrape_hotels(
                        booking_urls, 
                        progress_callback=update_progress,
                        max_concurrent=st.session_state.booking_max_concurrent
                    )
                )
                
                st.session_state.booking_results = results
                successful_count = len([r for r in results if r.get("status") == "publish"])
                failed_count = len(results) - successful_count
                
                # Calcular tiempo total
                total_time = loop.time() - start_time
                avg_time_per_url = total_time / len(booking_urls) if booking_urls else 0
                
                # Limpiar contenedores de progreso
                progress_container.empty()
                
                # Mostrar resumen final
                Alert.success(
                    f"✅ Scraping completado en {total_time:.1f} segundos\n"
                    f"• {successful_count} hoteles procesados exitosamente\n"
                    f"• {failed_count} con errores\n"
                    f"• Tiempo promedio: {avg_time_per_url:.1f} seg/URL"
                )
            except Exception as e:
                Alert.error(f"Error durante el scraping: {str(e)}")
                progress_container.empty()
            finally:
                if 'loop' in locals() and loop.is_running():
                    loop.close()
    
    def _render_results_section(self):
        results = st.session_state.booking_results
        self._render_results_summary(results)
        self._render_export_options()
        DataDisplay.json(self._prepare_results_for_json(results), title="JSON Completo de Resultados", expanded=True)

    def _render_results_summary(self, results: List[Dict[str, Any]]):
        successful = [r for r in results if r.get("status") == "publish"]
        failed = [r for r in results if r.get("status") == "draft"]
        
        # Contar imágenes considerando el nuevo formato de objeto
        total_images = 0
        for r in successful:
            images = r.get("meta", {}).get("images", {})
            if isinstance(images, dict):
                total_images += len(images)
            elif isinstance(images, list):  # Compatibilidad con formato antiguo
                total_images += len(images)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total procesados", len(results))
        col2.metric("Exitosos", len(successful))
        col3.metric("Con errores", len(failed))
        col4.metric("Imágenes extraídas (exitosos)", total_images)
    
    def _render_export_options(self):
        st.session_state.booking_export_filename = st.text_input(
            "📄 Nombre del archivo para exportar:", value=st.session_state.booking_export_filename
        )
        col1, col2, col3 = st.columns(3)
        with col1: self._render_download_button()
        with col2: self._render_drive_upload_button()
        with col3: self._render_mongodb_upload_button()
    
    def _render_download_button(self):
        json_bytes = json.dumps(self._prepare_results_for_json(st.session_state.booking_results), ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button("⬇️ Descargar JSON", json_bytes, st.session_state.booking_export_filename, "application/json")
    
    def _render_drive_upload_button(self):
        if st.button("☁️ Subir a Drive", type="secondary"):
            if "proyecto_id" not in st.session_state:
                Alert.warning("Selecciona un proyecto en la barra lateral")
                return
            try:
                json_bytes = json.dumps(self._prepare_results_for_json(st.session_state.booking_results), ensure_ascii=False, indent=2).encode("utf-8")
                folder_id = self.drive_service.get_or_create_folder("scraping booking", st.session_state.proyecto_id)
                link = self.drive_service.upload_file(st.session_state.booking_export_filename, json_bytes, folder_id)
                if link: Alert.success(f"Archivo subido: [Ver en Drive]({link})")
                else: Alert.error("Error al subir archivo a Drive")
            except Exception as e: Alert.error(f"Error al subir a Drive: {str(e)}")

    def _add_project_metadata_to_hotels(self, hotels: List[Dict[str, Any]], proyecto_activo: str, proyecto_normalizado: str) -> List[Dict[str, Any]]:
        timestamp = datetime.now().isoformat()
        return [
            {**copy.deepcopy(hotel), "_guardado_manual": timestamp, "_proyecto_activo": proyecto_activo, "_proyecto_normalizado": proyecto_normalizado}
            for hotel in hotels
        ]

    async def _process_image_download_for_hotel(self, mongo_id: Any, hotel_data: Dict[str, Any], collection_name: str, database_name: str):
        hotel_name = hotel_data.get("meta", {}).get("nombre_alojamiento", f"Hotel ID {mongo_id}")
        st.info(f"📥 Descarga imágenes para: {hotel_name} (ID: {mongo_id})")
        try:
            result = await self.image_download_service.trigger_download(mongo_id, database_name=database_name, collection_name=collection_name)
            if result.get("success"):
                Alert.info(f"✅ Descarga para {hotel_name} iniciada (images-service). Job ID: {result.get('response', {}).get('job_id', 'N/A')}")
            else:
                Alert.warning(f"⚠️ Images-service falló para {hotel_name}. Intentando descarga directa...")
                direct_result = await self.direct_download_service.download_images_from_document(mongo_id, hotel_data, collection_name, database_name)
                if direct_result.get("success"):
                    Alert.success(f"✅ Imágenes descargadas (directo) para {hotel_name}: {direct_result.get('downloaded',0)}/{direct_result.get('total_images',0)}")
                else:
                    Alert.error(f"❌ Error descarga directa para {hotel_name}: {direct_result.get('error', 'Desconocido')}")
        except Exception as e:
            Alert.error(f"Excepción descarga imágenes para {hotel_name}: {e}")
            logger.error(f"Excepción descarga imágenes para {hotel_name} (ID: {mongo_id}): {e}")

    def _trigger_batch_image_downloads(self, mongo_ids: List[Any], successful_hotels_data: List[Dict[str, Any]], collection_name: str):
        if not mongo_ids: return
        database_name = st.secrets["mongodb"]["db"]
        with LoadingSpinner.show(f"🖼️ Procesando descarga de imágenes para {len(mongo_ids)} hoteles..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                tasks = [self._process_image_download_for_hotel(mongo_id, successful_hotels_data[i], collection_name, database_name)
                         for i, mongo_id in enumerate(mongo_ids) if i < len(successful_hotels_data)]
                if tasks: loop.run_until_complete(asyncio.gather(*tasks))
            finally:
                loop.close()
    
    def _render_mongodb_upload_button(self):
        if st.button("📤 Enviar a n8n", type="secondary"):
            try:
                successful_hotels = [r for r in st.session_state.booking_results if r.get("status") == "publish"]
                if not successful_hotels:
                    Alert.warning("No hay hoteles procesados exitosamente para enviar.")
                    return

                # Enviar directamente los datos completos a n8n (sin subir a MongoDB)
                n8n_notification_result = self.booking_service.notify_n8n_webhook(successful_hotels)
                if n8n_notification_result.get("success"):
                    Alert.success(n8n_notification_result.get("message"))
                    
                    # Mostrar el JSON de respuesta del webhook
                    if "response" in n8n_notification_result:
                        with st.expander("📋 Respuesta del webhook n8n", expanded=True):
                            st.json(n8n_notification_result["response"])
                            
                            # También mostrar los datos enviados
                            if "sent_data" in n8n_notification_result:
                                st.subheader("📤 Datos enviados:")
                                st.json(n8n_notification_result["sent_data"])
                else:
                    Alert.error(n8n_notification_result.get("message", "Error desconocido al notificar a n8n."))

            except Exception as e:
                Alert.error(f"Error general al enviar a n8n: {str(e)}")
                logger.error(f"Error detallado al enviar a n8n: {e}", exc_info=True)

    def _parse_urls(self, text: str) -> List[str]:
        lines = text.strip().split('\n')
        return [line.strip() for line in lines if line.strip() and line.startswith('http')]
    
    def _prepare_results_for_json(self, data):
        if isinstance(data, list):
            # Convertir lista a diccionario con claves "post-X"
            result_dict = {}
            for i, item in enumerate(data):
                result_dict[f"post-{i}"] = self._prepare_results_for_json(item)
            return result_dict
        elif isinstance(data, dict):
            return {k: self._prepare_results_for_json(v) for k, v in data.items()}
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId': # Mejorar la detección de ObjectId
            return str(data)
        return data
    
    def _clear_results(self):
        st.session_state.booking_results = []
        st.rerun()
