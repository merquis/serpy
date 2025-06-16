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

logger = logging.getLogger(__name__)

class BookingExtraerDatosPage:
    """Página para extraer datos de hoteles de Booking.com"""
    
    def __init__(self):
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
        if "booking_urls_input" not in st.session_state:
            st.session_state.booking_urls_input = "https://www.booking.com/hotel/es/hotelvinccilaplantaciondelsur.es.html?checkin=2025-07-10&checkout=2025-07-15&group_adults=2&group_children=0&no_rooms=1&dest_type=hotel"
        if "booking_results" not in st.session_state:
            st.session_state.booking_results = []
        if "booking_export_filename" not in st.session_state:
            st.session_state.booking_export_filename = "hoteles_booking.json"
        if "booking_input_mode" not in st.session_state:
            st.session_state.booking_input_mode = "URL manual"
        if "selected_mongo_doc" not in st.session_state:
            st.session_state.selected_mongo_doc = None
    
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
        # Radio buttons para seleccionar el modo de entrada
        st.session_state.booking_input_mode = st.radio(
            "Selecciona el origen de las URLs:",
            ["URL manual", "Desde MongoDB"],
            horizontal=True,
            index=0 if st.session_state.booking_input_mode == "URL manual" else 1
        )
        
        if st.session_state.booking_input_mode == "URL manual":
            # Modo manual - textarea para introducir URLs
            st.session_state.booking_urls_input = st.text_area(
                "📝 Pega URLs de hoteles de Booking:",
                value=st.session_state.booking_urls_input,
                height=150,
                help="""Puedes introducir:
                - URLs separadas por líneas
                - URLs separadas por comas
                - Un JSON con resultados de búsqueda (con campo 'hotels' que contenga 'url_arg')"""
            )
            
            # Mostrar estadísticas de URLs
            urls = self.booking_service.parse_urls_input(st.session_state.booking_urls_input)
            if urls:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("URLs válidas", len(urls))
                with col2:
                    st.metric("URLs de Booking", len([u for u in urls if "booking.com/hotel/" in u]))
                with col3:
                    st.metric("Otras URLs", len([u for u in urls if "booking.com/hotel/" not in u]))
                
                # Mostrar preview de TODAS las URLs
                with st.expander("🔍 Vista previa de URLs detectadas", expanded=False):
                    for i, url in enumerate(urls):
                        st.write(f"{i+1}. {url}")
        
        else:  # Desde MongoDB
            # Verificar que hay un proyecto activo
            if not st.session_state.get("proyecto_nombre"):
                Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
                return
            
            # Obtener el nombre del proyecto activo y normalizarlo
            proyecto_activo = st.session_state.proyecto_nombre
            
            # Importar la función de normalización y aplicarla
            from config.settings import normalize_project_name
            proyecto_normalizado = normalize_project_name(proyecto_activo)
            
            # Crear nombre de colección con proyecto normalizado
            # Usar sufijo centralizado desde settings
            from config.settings import get_collection_name
            collection_name = get_collection_name(proyecto_activo, "buscar_hoteles_booking")
            
            try:
                # Obtener todos los documentos de la colección del proyecto
                documents = self.get_mongo_repo().find_many(
                    filter_dict={},  # Sin filtro para obtener todos
                    collection_name=collection_name,
                    limit=100,  # Limitar a 100 documentos más recientes
                    sort=[("_id", -1)]  # Ordenar por _id descendente (más recientes primero)
                )
                
                if documents:
                    # Crear opciones para el selectbox
                    options = []
                    for doc in documents:
                        # Crear una etiqueta descriptiva para cada documento
                        label = f"{doc.get('search_params', {}).get('destination', 'Sin destino')} - "
                        label += f"Check-in: {doc.get('search_params', {}).get('checkin', 'N/A')} - "
                        label += f"{len(doc.get('hotels', []))} hoteles - "
                        label += f"ID: {str(doc.get('_id', ''))[-12:]}"
                        options.append((label, doc))
                    
                    # Selectbox para elegir documento
                    selected_option = st.selectbox(
                        "Selecciona un documento de MongoDB:",
                        options=range(len(options)),
                        format_func=lambda x: options[x][0]
                    )
                    
                    if selected_option is not None:
                        st.session_state.selected_mongo_doc = options[selected_option][1]
                        
                        # Mostrar información del documento seleccionado
                        doc = st.session_state.selected_mongo_doc
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total hoteles", len(doc.get('hotels', [])))
                        with col2:
                            st.metric("Destino", doc.get('search_params', {}).get('destination', 'N/A'))
                        with col3:
                            st.metric("Fecha búsqueda", doc.get('fecha_busqueda', 'N/A')[:10])
                        
                        # Mostrar preview de hoteles - MOSTRAR TODOS (cerrado por defecto)
                        with st.expander("🏨 Vista previa de hoteles", expanded=False):
                            hotels = doc.get('hotels', [])
                            for i, hotel in enumerate(hotels):
                                st.write(f"{i+1}. **{hotel.get('nombre_hotel', 'Sin nombre')}**")
                                if hotel.get('url_arg'):
                                    # Mostrar URL completa sin cortar
                                    st.code(hotel['url_arg'], language=None)
                        
                        # Botón para cargar desde MongoDB
                        if st.button("📥 Cargar desde MongoDB", type="secondary"):
                            # Convertir el documento a JSON string para procesarlo
                            json_str = json.dumps(doc, default=str)
                            st.session_state.booking_urls_input = json_str
                            st.success(f"✅ Cargados {len(hotels)} hoteles desde MongoDB")
                else:
                    st.warning(f"No se encontraron documentos en la colección '{collection_name}'")
                    st.info(f"📊 Cargando desde colección: **{collection_name}** (proyecto: {proyecto_activo})")
                    
            except Exception as e:
                st.error(f"Error al conectar con MongoDB: {str(e)}")
    
    def _render_scraping_section(self):
        """Renderiza la sección de scraping"""
        col1, col2 = st.columns([3, 1])

        if "scraping_in_progress" not in st.session_state:
            st.session_state.scraping_in_progress = False

        with col1:
            scrape_btn = st.button("🔍 Scrapear Hoteles", type="primary", use_container_width=True, disabled=st.session_state.scraping_in_progress)
            # Solo marcar el estado, no lanzar el scraping aquí
            if scrape_btn and not st.session_state.scraping_in_progress:
                st.session_state.scraping_in_progress = True

        # Lanzar el scraping automáticamente si el estado lo indica
        if st.session_state.scraping_in_progress and not st.session_state.get("scraping_already_launched", False):
            st.session_state.scraping_already_launched = True
            self._perform_scraping()
        elif not st.session_state.scraping_in_progress:
            st.session_state.scraping_already_launched = False
        
        with col2:
            if st.session_state.booking_results:
                if st.button("🧹 Limpiar", type="secondary", use_container_width=True, disabled=st.session_state.scraping_in_progress):
                    self._clear_results()
    
    def _perform_scraping(self):
        """Ejecuta el scraping de las URLs"""
        urls = self.booking_service.parse_urls_input(st.session_state.booking_urls_input)
        booking_urls = [url for url in urls if "booking.com/hotel/" in url]

        if not booking_urls:
            Alert.warning("No se encontraron URLs válidas de Booking.com")
            st.session_state.scraping_in_progress = False
            return

        # Contenedor de progreso
        progress_container = st.empty()

        def update_progress(info: Dict[str, Any]):
            # El callback recibe un diccionario, no un string
            message = info.get("message", "Procesando...")
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
                st.session_state.scraping_in_progress = False
                st.rerun()

            except Exception as e:
                Alert.error(f"Error durante el scraping: {str(e)}")
                st.session_state.scraping_in_progress = False
            finally:
                loop.close()
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        results = st.session_state.booking_results
        
        # Resumen de resultados
        self._render_results_summary(results)
        
        # Opciones de exportación
        self._render_export_options()
        
        # Mostrar solo el JSON de exportación, sin expanders ni tarjetas de hoteles
        json_export = self._prepare_results_for_json(results)
        DataDisplay.json(
            json_export,
            title="JSON Completo (estructura exportación)",
            expanded=True
        )

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
        if st.button("☁️ Subir a Drive", type="secondary"):
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
        if st.button("📤 Subir a MongoDB", type="secondary"):
            try:
                # Verificar que hay un proyecto activo
                if not st.session_state.get("proyecto_nombre"):
                    Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
                    return
                
                # Obtener el nombre del proyecto activo y normalizarlo
                proyecto_activo = st.session_state.proyecto_nombre
                
                # Importar la función de normalización y aplicarla
                from config.settings import normalize_project_name
                proyecto_normalizado = normalize_project_name(proyecto_activo)
                
                # Usar sufijo centralizado desde settings
                from config.settings import get_collection_name
                collection_name = get_collection_name(proyecto_activo, "extraer_hoteles_booking")
                
                # Solo subir hoteles exitosos
                successful_hotels = [r for r in st.session_state.booking_results if not r.get("error")]
                
                if not successful_hotels:
                    Alert.warning("No hay hoteles exitosos para subir")
                    return
                
                # Agregar metadatos del proyecto a cada hotel
                import copy
                from datetime import datetime
                
                hotels_with_metadata = []
                timestamp = datetime.now().isoformat()
                
                for hotel in successful_hotels:
                    hotel_with_metadata = copy.deepcopy(hotel)
                    hotel_with_metadata["_guardado_manual"] = timestamp
                    hotel_with_metadata["_proyecto_activo"] = proyecto_activo
                    hotel_with_metadata["_proyecto_normalizado"] = proyecto_normalizado
                    hotels_with_metadata.append(hotel_with_metadata)
                
                # Insertar en MongoDB
                if len(hotels_with_metadata) > 1:
                    inserted_ids = self.get_mongo_repo().insert_many(
                        hotels_with_metadata,
                        collection_name=collection_name
                    )
                    Alert.success(f"✅ {len(inserted_ids)} hoteles subidos a MongoDB (colección: {collection_name})")

                    # Enviar IDs a n8n
                    try:
                        n8n_url = settings.N8N_WEBHOOK_URL
                        ids = [{"_id": str(id)} for id in inserted_ids]
                        data = ids
                        response = requests.post(n8n_url, json=data)
                        response.raise_for_status()
                        logger.info(f"✅ IDs enviados a n8n: {ids}")
                        st.success(f"✅ IDs enviados a n8n correctamente a la URL: {n8n_url}")
                    except requests.exceptions.RequestException as e:
                        logger.error(f"❌ Error al enviar IDs a n8n: {e}")

                    # Ejecutar descarga de imágenes para cada hotel
                    with LoadingSpinner.show("🖼️ Iniciando descarga de imágenes..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        try:
                            # Crear servicio de descarga directa como fallback
                            direct_download_service = DirectImageDownloadService()

                            for i, mongo_id in enumerate(inserted_ids):
                                hotel_name = successful_hotels[i].get("nombre_alojamiento", "")
                                st.info(f"📥 Descargando imágenes para: {hotel_name} (ID: {mongo_id})")

                                # Obtener el nombre de la base de datos desde los secrets
                                database_name = st.secrets["mongodb"]["db"]

                                # Intentar primero con el images-service
                                result = loop.run_until_complete(
                                    self.image_download_service.trigger_download(
                                        mongo_id,
                                        database_name=database_name,
                                        collection_name=collection_name
                                    )
                                )

                                if result["success"]:
                                    st.success(f"✅ Descarga iniciada para {hotel_name} (images-service)")
                                else:
                                    # Si falla el images-service, usar descarga directa
                                    st.warning(f"⚠️ Images-service no disponible, usando descarga directa...")

                                    # Usar descarga directa con los datos del hotel
                                    direct_result = loop.run_until_complete(
                                        direct_download_service.download_images_from_document(
                                            mongo_id,
                                            successful_hotels[i],
                                            collection_name,
                                            database_name
                                        )
                                    )

                                    if direct_result["success"]:
                                        st.success(f"✅ Imágenes descargadas directamente para {hotel_name}")
                                        st.info(f"📁 Guardadas en: {direct_result['storage_path']}")
                                        st.info(f"📊 {direct_result['downloaded']}/{direct_result['total_images']} imágenes descargadas")
                                    else:
                                        st.error(f"❌ Error en descarga directa: {direct_result.get('error', 'Error desconocido')}")
                        finally:
                            loop.close()
                else:
                    # Un solo hotel - agregar metadatos
                    hotel_with_metadata = copy.deepcopy(successful_hotels[0])
                    hotel_with_metadata["_guardado_manual"] = timestamp
                    hotel_with_metadata["_proyecto_activo"] = proyecto_activo
                    hotel_with_metadata["_proyecto_normalizado"] = proyecto_normalizado

                    inserted_id = self.get_mongo_repo().insert_one(
                        hotel_with_metadata,
                        collection_name=collection_name
                    )
                    Alert.success(f"✅ Hotel subido a MongoDB (colección: {collection_name}) con ID: `{inserted_id}`")

                    # Enviar ID a n8n
                    try:
                        n8n_url = settings.N8N_WEBHOOK_URL
                        ids = [{"_id": str(inserted_id)}]
                        data = ids
                        response = requests.post(n8n_url, json=data)
                        response.raise_for_status()
                        logger.info(f"✅ ID enviado a n8n: {inserted_id}")
                        st.success(f"✅ ID enviado a n8n correctamente a la URL: {n8n_url}")
                    except requests.exceptions.RequestException as e:
                        logger.error(f"❌ Error al enviar ID a n8n: {e}")

                    # Ejecutar descarga de imágenes
                    with LoadingSpinner.show("🖼️ Iniciando descarga de imágenes..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        try:
                            hotel_name = successful_hotels[0].get("nombre_alojamiento", "")
                            st.info(f"📥 Descargando imágenes para: {hotel_name} (ID: {inserted_id})")

                            # Obtener el nombre de la base de datos desde los secrets
                            database_name = st.secrets["mongodb"]["db"]

                            # Usar el mismo nombre de colección que se usó para guardar en MongoDB
                            result = loop.run_until_complete(
                                self.image_download_service.trigger_download(
                                    inserted_id,
                                    database_name=database_name,
                                    collection_name=collection_name  # Usar la misma colección que se creó
                                )
                            )

                            # Mostrar el comando curl utilizado
                            st.info(f"🔗 Comando CURL utilizado:")
                            st.code(result.get("curl_cmd", ""), language="bash")

                            if result["success"]:
                                st.success(f"✅ Descarga de imágenes iniciada exitosamente")
                                st.info(f"Respuesta del servicio: {result.get('response', {})}")
                            else:
                                st.warning(f"⚠️ Error al descargar imágenes: {result.get('error', 'Error desconocido')}")
                                if 'status_code' in result:
                                    st.error(f"Status Code: {result['status_code']}")
                        finally:
                            loop.close()

            except Exception as e:
                Alert.error(f"Error al subir a MongoDB: {str(e)}")
    
    # Se elimina la visualización detallada de hoteles y errores, solo se muestra el JSON
    
    def _parse_urls(self, text: str) -> List[str]:
        """Parsea las URLs del texto de entrada (una por línea, versión original)"""
        lines = text.strip().split('\n')
        urls = []
        for line in lines:
            line = line.strip()
            if line and line.startswith('http'):
                urls.append(line)
        return urls
    
    def _prepare_results_for_json(self, data):
        """
        Prepara los resultados para serialización JSON.
        Mantiene la estructura plana sin campos comunes.
        """
        # Si es una lista de hoteles, devolverla tal como está
        if isinstance(data, list):
            return [self._prepare_results_for_json(item) for item in data]
        elif isinstance(data, dict):
            return {k: self._prepare_results_for_json(v) for k, v in data.items()}
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId':
            return str(data)
        else:
            return data
    
    def _clear_results(self):
        """Limpia los resultados"""
        st.session_state.booking_results = []
        st.rerun()
