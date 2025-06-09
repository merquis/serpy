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
from repositories.mongo_repository import MongoRepository
from config import config

class BookingExtraerDatosPage:
    """Página para extraer datos de hoteles de Booking.com"""
    
    def __init__(self):
        self.booking_service = BookingExtraerDatosService()
        self.drive_service = DriveService()
        self.image_download_service = SimpleImageDownloadService()
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
            # Obtener documentos de la colección hoteles-booking-urls
            try:
                # Obtener todos los documentos de la colección
                documents = self.mongo_repo.find_many(
                    filter_dict={},  # Sin filtro para obtener todos
                    collection_name="hoteles-booking-urls",
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
                    st.warning("No se encontraron documentos en la colección 'hoteles-booking-urls'")
                    
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
                # Solo subir hoteles exitosos
                successful_hotels = [r for r in st.session_state.booking_results if not r.get("error")]
                
                if not successful_hotels:
                    Alert.warning("No hay hoteles exitosos para subir")
                    return
                
                # Insertar en MongoDB
                if len(successful_hotels) > 1:
                    inserted_ids = self.mongo_repo.insert_many(
                        successful_hotels,
                        collection_name="hotel-booking"
                    )
                    Alert.success(f"✅ {len(inserted_ids)} hoteles subidos a MongoDB")
                    
                    # Ejecutar descarga de imágenes para cada hotel
                    with LoadingSpinner.show("🖼️ Iniciando descarga de imágenes..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            for i, mongo_id in enumerate(inserted_ids):
                                hotel_name = successful_hotels[i].get("nombre_alojamiento", "")
                                st.info(f"📥 Descargando imágenes para: {hotel_name} (ID: {mongo_id})")
                                
                                # Obtener el nombre de la base de datos desde los secrets
                                database_name = st.secrets["mongodb"]["db"]
                                
                                result = loop.run_until_complete(
                                    self.image_download_service.trigger_download(
                                        mongo_id,
                                        database_name=database_name,
                                        collection_name="hotel-booking"
                                    )
                                )
                                
                                if result["success"]:
                                    st.success(f"✅ Descarga iniciada para {hotel_name}")
                                else:
                                    st.warning(f"⚠️ Error al descargar imágenes de {hotel_name}: {result.get('error', 'Error desconocido')}")
                        finally:
                            loop.close()
                else:
                    inserted_id = self.mongo_repo.insert_one(
                        successful_hotels[0],
                        collection_name="hotel-booking"
                    )
                    Alert.success(f"✅ Hotel subido a MongoDB con ID: `{inserted_id}`")
                    
                    # Ejecutar descarga de imágenes
                    with LoadingSpinner.show("🖼️ Iniciando descarga de imágenes..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            hotel_name = successful_hotels[0].get("nombre_alojamiento", "")
                            st.info(f"📥 Descargando imágenes para: {hotel_name} (ID: {inserted_id})")
                            
                            # Obtener el nombre de la base de datos desde los secrets
                            database_name = st.secrets["mongodb"]["db"]
                            
                            result = loop.run_until_complete(
                                self.image_download_service.trigger_download(
                                    inserted_id,
                                    database_name=database_name,
                                    collection_name="hotel-booking"
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
        
        # Mostrar JSON completo con campos comunes fuera si corresponde
        json_export = self._prepare_results_for_json(results)
        DataDisplay.json(
            json_export,
            title="JSON Completo (estructura exportación)",
            expanded=True
        )
    
    def _display_hotel_card(self, hotel: Dict[str, Any]):
        """Muestra una tarjeta con información del hotel"""
        # Crear un expander para cada hotel con información resumida en el título
        # Usar SIEMPRE el nombre_hotel original si existe
        nombre_hotel = hotel.get('nombre_hotel', 'Sin nombre')
        valoracion = hotel.get('valoracion_global', 'N/A')
        ciudad = hotel.get('ciudad', 'N/A')
        num_imagenes = len(hotel.get('imagenes', []))
        
        # Título del expander solo con el nombre del hotel
        expander_title = f"{nombre_hotel}"

        with st.expander(expander_title, expanded=False):
            # Información básica en columnas compactas
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Opiniones:** {hotel.get('numero_opiniones', 0)}")
                st.write(f"**Precio:** {hotel.get('rango_precios', 'N/A')}")
            with col2:
                st.write(f"**Valoración:** {valoracion}/10")
            
            # Descripción
            descripcion = hotel.get('descripcion_corta')
            if descripcion:
                st.write("---")
                st.write("**📝 Descripción:**")
                st.write(descripcion)
            
            # Servicios
            servicios = hotel.get('servicios_principales', [])
            if servicios:
                st.write("---")
                st.write(f"**🛎️ Servicios disponibles ({len(servicios)}):**")
                # Mostrar servicios en columnas
                cols = st.columns(3)
                for i, servicio in enumerate(servicios[:9]):  # Mostrar solo los primeros 9
                    cols[i % 3].write(f"• {servicio}")
                if len(servicios) > 9:
                    st.caption(f"... y {len(servicios) - 9} servicios más")
            
            # Imágenes
            imagenes = hotel.get('imagenes', [])
            if imagenes:
                st.write("---")
                st.write(f"**🖼️ Imágenes ({len(imagenes)}):**")
                # Mostrar primera imagen como preview
                if len(imagenes) > 0:
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(imagenes[0], caption="Imagen principal", use_column_width=True)
                    with col2:
                        # Mostrar URLs en un área de texto compacta
                        st.write("**URLs de todas las imágenes:**")
                        urls_text = "\n".join(imagenes)
                        st.text_area("", value=urls_text, height=100, disabled=True, label_visibility="collapsed")
            
            # Enlace
            st.write("---")
            st.markdown(f"🔗 [Ver en Booking]({hotel.get('url_original', '')})")
    
    def _display_error_card(self, error: Dict[str, Any]):
        """Muestra una tarjeta de error"""
        with st.container():
            st.markdown(f"### ❌ Error: {error.get('error', 'Error desconocido')}")
            st.write(f"**URL:** {error.get('url_original', 'N/A')}")
            
            details = error.get('details')
            if details:
                st.write(f"**Detalles:** {details}")
            st.divider()
    
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
        Saca los campos comunes fuera del array de hoteles.
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
            return {k: self._prepare_results_for_json(v) for k, v in data.items()}
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId':
            return str(data)
        else:
            return data
    
    def _clear_results(self):
        """Limpia los resultados"""
        st.session_state.booking_results = []
        st.rerun()
