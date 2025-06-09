"""
Página de UI para Scraping de Etiquetas HTML
"""
import streamlit as st
import json
import asyncio
from typing import Dict, Any, Optional
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.google_extraer_datos_service import GoogleExtraerDatosService
from services.lista_extraer_datos_service import ListaExtraerDatosService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
from config import config

class GoogleExtraerDatosPage:
    """Página para extraer estructura jerárquica de etiquetas HTML"""
    
    def __init__(self):
        self.tag_service = GoogleExtraerDatosService()
        self.lista_service = ListaExtraerDatosService()
        self.drive_service = DriveService()
        self._mongo_repo = None  # Inicializar solo cuando se necesite
        self._init_session_state()
    
    @property
    def mongo_repo(self):
        """Lazy loading de MongoDB - solo se conecta cuando se necesita"""
        if self._mongo_repo is None:
            try:
                self._mongo_repo = MongoRepository(
                    uri=config.mongo_uri,
                    db_name=config.app.mongo_default_db
                )
            except Exception as e:
                st.error(f"Error conectando a MongoDB: {str(e)}")
                raise
        return self._mongo_repo
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "json_content" not in st.session_state:
            st.session_state.json_content = None
        if "json_filename" not in st.session_state:
            st.session_state.json_filename = None
        if "tag_results" not in st.session_state:
            st.session_state.tag_results = None
        if "export_filename" not in st.session_state:
            st.session_state.export_filename = "etiquetas_jerarquicas.json"
        # Variables para modo URL manual
        if "selected_tags" not in st.session_state:
            st.session_state.selected_tags = ["title", "description", "h1", "h2", "h3"]
        if "manual_urls_results" not in st.session_state:
            st.session_state.manual_urls_results = None
    
    def render(self):
        """Renderiza la página completa"""
        st.title("🏷️ Scraping de Etiquetas HTML")
        st.markdown("### � Extrae etiquetas SEO desde URLs manuales o archivos JSON")
        
        # Selector de fuente
        self._render_source_selector()
        
        # Mostrar configuración si hay archivo cargado
        if st.session_state.json_content and not st.session_state.tag_results:
            self._render_processing_section()
        
        # Mostrar resultados si existen
        if st.session_state.tag_results:
            self._render_results_section()
    
    def _render_source_selector(self):
        """Renderiza el selector de fuente del archivo"""
        source = st.radio(
            "Selecciona fuente del archivo:",
            ["URL manual", "Desde Drive", "Desde ordenador", "Desde MongoDB"],
            horizontal=True,
            index=0
        )
        
        if source == "URL manual":
            self._handle_manual_urls()
        elif source == "Desde ordenador":
            self._handle_file_upload()
        elif source == "Desde Drive":
            self._handle_drive_selection()
        else:  # Desde MongoDB
            self._handle_mongodb_selection()
    
    def _handle_manual_urls(self):
        """Maneja la entrada manual de URLs (integra funcionalidad de lista_extraer_datos)"""
        st.markdown("#### 🌍 URLs a Analizar")
        
        url_input = st.text_area(
            "Introduce una o varias URLs (una por línea o separadas por comas)",
            height=150,
            placeholder="https://ejemplo1.com\nhttps://ejemplo2.com\nejemplo3.com",
            help="Puedes introducir URLs con o sin protocolo. Se añadirá https:// automáticamente si es necesario."
        )
        
        if url_input:
            # Procesar y validar URLs
            raw_urls = [u.strip() for u in url_input.replace(",", "\n").split("\n") if u.strip()]
            valid_urls, invalid_urls = self.lista_service.validate_urls(raw_urls)
            
            # Mostrar estadísticas
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total URLs", len(raw_urls))
            with col2:
                st.metric("URLs válidas", len(valid_urls))
            with col3:
                st.metric("URLs inválidas", len(invalid_urls))
            
            # Mostrar URLs inválidas si las hay
            if invalid_urls:
                with st.expander("⚠️ URLs inválidas", expanded=False):
                    for url in invalid_urls:
                        st.warning(f"• {url}")
            
            # Guardar URLs válidas
            st.session_state.valid_urls = valid_urls
            
            # Sección de selección de etiquetas
            self._render_tag_selection_section()
            
            # Configuración avanzada
            self._render_advanced_settings()
            
            # Botón de ejecución
            self._render_manual_execution_section()
        else:
            st.info("ℹ️ Introduce al menos una URL para comenzar")
            st.session_state.valid_urls = []
        
        # Mostrar resultados si existen
        if st.session_state.manual_urls_results:
            self._render_manual_results_section()
    
    def _render_tag_selection_section(self):
        """Renderiza la sección de selección de etiquetas"""
        st.markdown("---")
        st.markdown("#### 🏷️ Etiquetas a Extraer")
        
        # Etiquetas disponibles
        available_tags = {
            "title": "Title",
            "description": "Meta Description",
            "h1": "H1 (primer heading)",
            "h2": "H2 (todos)",
            "h3": "H3 (todos)",
            "canonical": "URL Canónica",
            "og:title": "Open Graph Title",
            "og:description": "Open Graph Description"
        }
        
        # Selector de etiquetas
        selected_tags = st.multiselect(
            "Selecciona las etiquetas HTML que deseas extraer",
            options=list(available_tags.keys()),
            default=st.session_state.selected_tags,
            format_func=lambda x: f"{available_tags[x]} ({x})",
            help="Las etiquetas seleccionadas se extraerán de cada URL"
        )
        
        st.session_state.selected_tags = selected_tags
        
        # Mostrar resumen
        if selected_tags:
            st.success(f"✅ Se extraerán {len(selected_tags)} etiquetas de cada URL")
        else:
            st.warning("⚠️ Selecciona al menos una etiqueta para extraer")
    
    def _render_advanced_settings(self):
        """Renderiza la configuración avanzada"""
        with st.expander("⚙️ Configuración Avanzada", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.max_workers = st.slider(
                    "Número de workers concurrentes",
                    min_value=1,
                    max_value=10,
                    value=5,
                    help="Más workers = más rápido pero más carga en el servidor"
                )
            
            with col2:
                st.session_state.timeout = st.slider(
                    "Timeout por URL (segundos)",
                    min_value=5,
                    max_value=60,
                    value=20,
                    help="Tiempo máximo de espera por cada URL"
                )
    
    def _render_manual_execution_section(self):
        """Renderiza la sección de ejecución para URLs manuales"""
        st.markdown("---")
        
        # Validar condiciones
        can_execute = (
            hasattr(st.session_state, 'valid_urls') and 
            st.session_state.valid_urls and 
            st.session_state.selected_tags
        )
        
        if Button.primary(
            "🔍 Extraer etiquetas",
            disabled=not can_execute,
            use_container_width=True,
            icon="🚀"
        ):
            self._execute_manual_scraping()
    
    def _execute_manual_scraping(self):
        """Ejecuta el proceso de scraping manual"""
        urls = st.session_state.valid_urls
        tags = st.session_state.selected_tags
        max_workers = st.session_state.get("max_workers", 5)
        timeout = st.session_state.get("timeout", 20)
        
        with LoadingSpinner.show(f"Analizando {len(urls)} URLs..."):
            try:
                # Ejecutar scraping
                results = self.lista_service.scrape_urls(
                    urls=urls,
                    tags=tags,
                    max_workers=max_workers,
                    timeout=timeout
                )
                
                # Guardar resultados
                st.session_state.manual_urls_results = results
                
                # Estadísticas
                successful = sum(1 for r in results if r.get("status_code") == 200)
                failed = len(results) - successful
                
                if successful > 0:
                    Alert.success(f"✅ Scraping completado: {successful} URLs exitosas, {failed} fallidas")
                else:
                    Alert.error("❌ No se pudo extraer información de ninguna URL")
                
                st.rerun()
                
            except Exception as e:
                Alert.error(f"Error durante el scraping: {str(e)}")
    
    def _render_manual_results_section(self):
        """Renderiza la sección de resultados para URLs manuales"""
        st.markdown("---")
        st.markdown("### 📦 Resultados Obtenidos")
        
        results = st.session_state.manual_urls_results
        
        # Estadísticas generales
        self._render_manual_statistics(results)
        
        # Tabs para diferentes vistas
        tab1, tab2, tab3 = st.tabs(["📊 Vista General", "📄 Detalle por URL", "💾 JSON Completo"])
        
        with tab1:
            self._render_manual_overview(results)
        
        with tab2:
            self._render_manual_detailed_view(results)
        
        with tab3:
            self._render_manual_json_view(results)
        
        # Opciones de exportación
        self._render_manual_export_options(results)
    
    def _render_manual_statistics(self, results):
        """Renderiza estadísticas de los resultados manuales"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total URLs", len(results))
        
        with col2:
            successful = sum(1 for r in results if r.get("status_code") == 200)
            st.metric("Exitosas", successful)
        
        with col3:
            failed = sum(1 for r in results if r.get("status_code") != 200)
            st.metric("Fallidas", failed)
        
        with col4:
            success_rate = (successful / len(results) * 100) if results else 0
            st.metric("Tasa de éxito", f"{success_rate:.1f}%")
    
    def _render_manual_overview(self, results):
        """Renderiza vista general de resultados manuales"""
        for result in results:
            status = "✅" if result.get("status_code") == 200 else "❌"
            
            with st.expander(f"{status} {result['url']}", expanded=False):
                if result.get("status_code") == 200:
                    # Mostrar etiquetas extraídas
                    for tag in st.session_state.selected_tags:
                        if tag in result:
                            value = result[tag]
                            if isinstance(value, list):
                                st.write(f"**{tag}:** {len(value)} elementos")
                                if value:  # Mostrar primeros elementos
                                    for item in value[:3]:
                                        st.caption(f"  • {item}")
                                    if len(value) > 3:
                                        st.caption(f"  ... y {len(value) - 3} más")
                            else:
                                st.write(f"**{tag}:** {value or '(vacío)'}")
                else:
                    # Mostrar error
                    st.error(f"Error: {result.get('error', 'Código ' + str(result.get('status_code')))}")
    
    def _render_manual_detailed_view(self, results):
        """Renderiza vista detallada por URL para resultados manuales"""
        url_options = [r["url"] for r in results]
        selected_url = st.selectbox("Selecciona una URL:", url_options)
        
        if selected_url:
            result = next(r for r in results if r["url"] == selected_url)
            
            if result.get("status_code") == 200:
                for tag in st.session_state.selected_tags:
                    if tag in result:
                        Card.render(
                            title=f"🏷️ {tag}",
                            content=lambda value=result[tag]: self._display_manual_tag_value(value),
                            expandable=True,
                            expanded=False
                        )
            else:
                Alert.error(f"Error al procesar esta URL: {result.get('error', 'Desconocido')}")
    
    def _display_manual_tag_value(self, value):
        """Muestra el valor de una etiqueta de forma apropiada"""
        if isinstance(value, list):
            if value:
                for item in value:
                    st.write(f"• {item}")
            else:
                st.caption("(lista vacía)")
        else:
            st.write(value or "(vacío)")
    
    def _render_manual_json_view(self, results):
        """Renderiza vista JSON completa para resultados manuales"""
        DataDisplay.json(results, expanded=False)
    
    def _render_manual_export_options(self, results):
        """Renderiza opciones de exportación para resultados manuales"""
        st.markdown("---")
        st.markdown("#### 💾 Opciones de Exportación")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Descargar JSON
            json_data = json.dumps(results, indent=2, ensure_ascii=False)
            st.download_button(
                label="⬇️ Descargar JSON",
                data=json_data.encode("utf-8"),
                file_name="etiquetas_urls_manuales.json",
                mime="application/json"
            )
        
        with col2:
            # Subir a Drive
            if Button.secondary("☁️ Subir a Drive", icon="☁️"):
                self._upload_manual_to_drive(results)
        
        with col3:
            # Nueva extracción
            if Button.secondary("🔄 Nueva extracción", icon="🔄"):
                st.session_state.manual_urls_results = None
                st.rerun()
    
    def _upload_manual_to_drive(self, results):
        """Sube los resultados manuales a Google Drive"""
        if "proyecto_id" not in st.session_state:
            Alert.warning("Selecciona un proyecto en la barra lateral")
            return
        
        try:
            # Preparar datos
            json_bytes = json.dumps(results, indent=2, ensure_ascii=False).encode("utf-8")
            filename = f"etiquetas_manuales_{len(results)}_urls.json"
            
            # Obtener carpeta
            folder_id = self.drive_service.get_or_create_folder(
                "scraper urls manual",
                st.session_state.proyecto_id
            )
            
            # Subir archivo
            link = self.drive_service.upload_file(filename, json_bytes, folder_id)
            
            if link:
                Alert.success(f"✅ Archivo subido: [Ver en Drive]({link})")
            else:
                Alert.error("Error al subir archivo")
                
        except Exception as e:
            Alert.error(f"Error al subir a Drive: {str(e)}")
    
    def _handle_file_upload(self):
        """Maneja la carga de archivo desde el ordenador"""
        uploaded_file = st.file_uploader("Sube archivo JSON", type=["json"])
        
        if uploaded_file:
            st.session_state.json_content = uploaded_file.read()
            st.session_state.json_filename = uploaded_file.name
            st.session_state.tag_results = None
            Alert.success(f"Archivo {uploaded_file.name} cargado correctamente")
    
    def _handle_drive_selection(self):
        """Maneja la selección de archivo desde Drive"""
        if "proyecto_id" not in st.session_state:
            Alert.error("Selecciona primero un proyecto en la barra lateral")
            return
        
        try:
            # Obtener subcarpeta
            folder_id = self.drive_service.get_or_create_folder(
                "scraping google",
                st.session_state.proyecto_id
            )
            
            # Listar archivos JSON
            files = self.drive_service.list_json_files_in_folder(folder_id)
            
            if not files:
                Alert.warning("No hay archivos JSON en la carpeta 'scraping google'")
                return
            
            # Selector de archivo
            file_names = list(files.keys())
            selected_file = st.selectbox("Selecciona un archivo de Drive", file_names)
            
            if Button.primary("Cargar archivo de Drive", icon=config.ui.icons["download"]):
                # Descargar contenido
                content = self.drive_service.get_file_content(files[selected_file])
                st.session_state.json_content = content
                st.session_state.json_filename = selected_file
                st.session_state.tag_results = None
                Alert.success(f"Archivo {selected_file} cargado desde Drive")
                
        except Exception as e:
            Alert.error(f"Error al acceder a Drive: {str(e)}")
    
    def _handle_mongodb_selection(self):
        """Maneja la selección de documentos desde MongoDB"""
        try:
            # Obtener documentos de la colección "URLs Google"
            documents = self.mongo_repo.find_many(
                {},
                collection_name="URLs Google",
                limit=50  # Limitar a 50 documentos más recientes
            )
            
            if not documents:
                Alert.warning("No hay documentos en la colección 'URLs Google'")
                return
            
            # Crear opciones para el selector
            # Mostrar búsqueda y fecha si está disponible
            options = {}
            for doc in documents:
                # Crear una etiqueta descriptiva para cada documento
                busqueda = doc.get("busqueda", "Sin búsqueda")
                doc_id = str(doc.get("_id", ""))
                # Si es una lista, tomar el primer elemento
                if isinstance(busqueda, list) and busqueda:
                    busqueda = busqueda[0].get("busqueda", "Sin búsqueda") if isinstance(busqueda[0], dict) else str(busqueda[0])
                
                label = f"{busqueda} - ID: {doc_id}"  # ID completo
                options[label] = doc
            
            # Selector de documento
            selected_key = st.selectbox(
                "Selecciona un documento de MongoDB:",
                list(options.keys())
            )
            
            if Button.primary("Cargar desde MongoDB", icon="📥"):
                selected_doc = options[selected_key]
                
                # Convertir el documento a JSON
                # Eliminar el _id para evitar problemas de serialización
                if "_id" in selected_doc:
                    del selected_doc["_id"]
                
                content = json.dumps(selected_doc).encode()
                st.session_state.json_content = content
                st.session_state.json_filename = f"mongodb_{selected_key.replace(' - ID: ', '_')}.json"
                st.session_state.tag_results = None
                Alert.success(f"Documento cargado desde MongoDB: {selected_key}")
                
        except Exception as e:
            Alert.error(f"Error al acceder a MongoDB: {str(e)}")
    
    def _render_processing_section(self):
        """Renderiza la sección de procesamiento"""
        # Mostrar preview del JSON
        try:
            json_data = json.loads(st.session_state.json_content)
            
            with st.expander("📄 Vista previa del JSON cargado", expanded=False):
                st.json(json_data)
            
            # Configuración de concurrencia
            max_concurrent = st.slider(
                "🔁 Concurrencia máxima",
                min_value=1,
                max_value=10,
                value=5,
                help="Número máximo de URLs procesadas simultáneamente"
            )
            
            # Botón de procesamiento
            if Button.primary("Extraer estructura de etiquetas", icon="🔄"):
                self._process_urls(json_data, max_concurrent)
                
        except json.JSONDecodeError as e:
            Alert.error(f"Error al decodificar JSON: {str(e)}")
    
    def _process_urls(self, json_data: Any, max_concurrent: int):
        """Procesa las URLs del JSON"""
        # Título de procesamiento
        st.markdown("### 🔄 Procesando URLs...")
        
        # Contenedores para el progreso
        progress_container = st.container()
        
        with progress_container:
            # Métricas de progreso
            col1, col2, col3 = st.columns(3)
            with col1:
                completed_metric = st.empty()
                completed_metric.metric("✅ Completadas", "0/0")
            with col2:
                remaining_metric = st.empty()
                remaining_metric.metric("⏳ Restantes", "0")
            with col3:
                concurrent_metric = st.empty()
                concurrent_metric.metric("🔄 Concurrentes", "0")
            
            # Barra de progreso
            progress_bar = st.progress(0)
            
            # Información de URLs activas
            st.markdown("---")
            active_urls_container = st.empty()
            active_urls_container.info("Iniciando procesamiento...")
        
        def update_progress(progress_info):
            """Actualiza la visualización del progreso"""
            try:
                # Debug log
                print(f"Progress update received: {progress_info}")
                
                if isinstance(progress_info, dict):
                    # Información detallada del servicio Playwright
                    if "active_urls" in progress_info:
                        completed = progress_info.get("completed", 0)
                        total = progress_info.get("total", 1)
                        remaining = progress_info.get("remaining", 0)
                        active_urls = progress_info.get("active_urls", [])
                        
                        # Actualizar métricas - limpiar y recrear
                        completed_metric.empty()
                        completed_metric.metric("✅ Completadas", f"{completed}/{total}")
                        
                        remaining_metric.empty()
                        remaining_metric.metric("⏳ Restantes", remaining)
                        
                        concurrent_metric.empty()
                        concurrent_metric.metric("🔄 Concurrentes", len(active_urls))
                        
                        # Actualizar barra de progreso
                        progress = completed / total if total > 0 else 0
                        progress_bar.progress(progress)
                        
                        # Mostrar URLs activas
                        active_urls_container.empty()
                        if active_urls:
                            urls_display = "**🌐 URLs procesándose actualmente:**\n\n"
                            # Usar el índice real basado en las URLs completadas
                            for idx, url in enumerate(active_urls[:max_concurrent]):
                                # Calcular el número real de la URL (completadas + posición en activas + 1)
                                url_number = completed + idx + 1
                                # Truncar URL si es muy larga
                                display_url = url if len(url) <= 80 else url[:77] + "..."
                                urls_display += f"{url_number}. `{display_url}`\n"
                            active_urls_container.info(urls_display)
                        else:
                            active_urls_container.info("⏳ Esperando nuevas URLs...")
                    
                    # Información del servicio de tags
                    elif "urls_processed" in progress_info:
                        search_term = progress_info.get("search_term", "")
                        urls_processed = progress_info.get("urls_processed", 0)
                        total_urls = progress_info.get("total_urls", 0)
                        
                        if search_term:
                            active_urls_container.empty()
                            active_urls_container.info(f"🔍 Procesando búsqueda: **{search_term}**")
                    
                    # Información simple del mensaje
                    elif "message" in progress_info:
                        message = progress_info.get("message", "")
                        print(f"Message update: {message}")
                else:
                    # Mensaje simple (compatibilidad)
                    active_urls_container.empty()
                    active_urls_container.info(str(progress_info))
            except Exception as e:
                # Log error but don't break the process
                print(f"Error updating progress: {e}")
                import traceback
                traceback.print_exc()
        
        try:
            # Ejecutar scraping asíncrono
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(
                self.tag_service.scrape_tags_from_json(
                    json_data,
                    max_concurrent=max_concurrent,
                    progress_callback=update_progress
                )
            )
            
            st.session_state.tag_results = results
            
            # Generar nombre de archivo de exportación
            base_name = st.session_state.json_filename or "etiquetas"
            st.session_state.export_filename = base_name.replace(".json", "_ALL.json")
            
            # Contar URLs procesadas
            total_urls = sum(len(r.get("resultados", [])) for r in results)
            
            # Limpiar contenedores de progreso
            progress_container.empty()
            
            Alert.success(f"✅ Se procesaron {total_urls} URLs exitosamente")
            st.rerun()
            
        except Exception as e:
            Alert.error(f"Error durante el procesamiento: {str(e)}")
        finally:
            loop.close()
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        results = st.session_state.tag_results
        
        # Input para nombre de archivo
        st.session_state.export_filename = st.text_input(
            "📄 Nombre para exportar el archivo JSON",
            value=st.session_state.export_filename
        )
        
        # Botones de acción
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            self._render_download_button()
        
        with col2:
            self._render_drive_upload_button()
        
        with col3:
            self._render_mongodb_upload_button()
        
        with col4:
            if Button.secondary("Nueva extracción", icon=config.ui.icons["clean"]):
                self._clear_results()
        
        # Mostrar resultados
        self._display_results(results)
    
    def _render_download_button(self):
        """Renderiza el botón de descarga"""
        # Convertir ObjectIds a strings antes de serializar
        results_for_json = self._prepare_results_for_json(st.session_state.tag_results)
        
        json_bytes = json.dumps(
            results_for_json,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")
        
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name=st.session_state.export_filename,
            mime="application/json"
        )
    
    def _prepare_results_for_json(self, data):
        """Prepara los resultados para serialización JSON convirtiendo ObjectIds a strings"""
        if isinstance(data, dict):
            return {k: self._prepare_results_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._prepare_results_for_json(item) for item in data]
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId':
            return str(data)
        else:
            return data
    
    def _render_drive_upload_button(self):
        """Renderiza el botón de subida a Drive"""
        if Button.secondary("Subir a Drive", icon=config.ui.icons["upload"]):
            if "proyecto_id" not in st.session_state:
                Alert.warning("Selecciona un proyecto en la barra lateral")
                return
            
            try:
                # Convertir a JSON (convirtiendo ObjectIds a strings)
                results_for_json = self._prepare_results_for_json(st.session_state.tag_results)
                json_bytes = json.dumps(
                    results_for_json,
                    ensure_ascii=False,
                    indent=2
                ).encode("utf-8")
                
                # Obtener carpeta
                folder_id = self.drive_service.get_or_create_folder(
                    "scraping etiquetas html",
                    st.session_state.proyecto_id
                )
                
                # Subir archivo
                link = self.drive_service.upload_file(
                    st.session_state.export_filename,
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
                # Determinar si es un solo documento o múltiples
                data = st.session_state.tag_results
                
                if isinstance(data, list) and len(data) > 1:
                    # Insertar múltiples documentos
                    inserted_ids = self.mongo_repo.insert_many(
                        data,
                        collection_name="hoteles"
                    )
                    ids_formatted = "\n".join([f"- `{_id}`" for _id in inserted_ids])
                    Alert.success(
                        f"Subidos {len(inserted_ids)} documentos a MongoDB:\n\n{ids_formatted}"
                    )
                else:
                    # Insertar un solo documento
                    doc = data[0] if isinstance(data, list) else data
                    inserted_id = self.mongo_repo.insert_one(
                        doc,
                        collection_name="hoteles"
                    )
                    Alert.success(f"Documento subido a MongoDB con ID: `{inserted_id}`")
                    
            except Exception as e:
                Alert.error(f"Error al subir a MongoDB: {str(e)}")
    
    def _clear_results(self):
        """Limpia los resultados y el estado"""
        st.session_state.json_content = None
        st.session_state.json_filename = None
        st.session_state.tag_results = None
        st.session_state.export_filename = "etiquetas_jerarquicas.json"
        st.rerun()
    
    def _display_results(self, results: list):
        """Muestra los resultados del scraping"""
        st.subheader("📦 Resultados estructurados")
        
        # Resumen
        total_searches = len(results)
        total_urls = sum(len(r.get("resultados", [])) for r in results)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Búsquedas procesadas", total_searches)
        with col2:
            st.metric("URLs analizadas", total_urls)
        
        # Mostrar resultados por búsqueda
        for result in results:
            search_term = result.get("busqueda", "Sin término")
            urls_count = len(result.get("resultados", []))
            
            with st.expander(f"🔍 {search_term} - {urls_count} URLs"):
                # Información de contexto
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Idioma:** {result.get('idioma', 'N/A')}")
                with col2:
                    st.write(f"**Región:** {result.get('region', 'N/A')}")
                with col3:
                    st.write(f"**Dominio:** {result.get('dominio', 'N/A')}")
                
                # Resultados por URL
                for url_result in result.get("resultados", []):
                    self._display_url_result(url_result)
        
        # Mostrar JSON completo
        DataDisplay.json(
            results,
            title="JSON Completo",
            expanded=True
        )
    
    def _display_url_result(self, url_result: Dict[str, Any]):
        """Muestra el resultado de una URL individual"""
        url = url_result.get("url", "")
        status = url_result.get("status_code", "N/A")
        
        # Crear contenedor para la URL
        with st.container():
            # Header con URL y status
            if status == "error":
                st.markdown(f"❌ **{url}** - Error: {url_result.get('error', 'Unknown')}")
            else:
                st.markdown(f"✅ **{url}** - Status: {status} - Método: {url_result.get('method', 'N/A')}")
                
                # Mostrar metadatos principales
                col1, col2 = st.columns(2)
                with col1:
                    title = url_result.get("title", "")
                    if title:
                        st.markdown("**📄 Title:**")
                        st.info(title)
                
                with col2:
                    description = url_result.get("description", "")
                    if description:
                        st.markdown("**📝 Description:**")
                        st.info(description)
                
                # Mostrar primer H1
                primer_h1 = url_result.get("primer_h1", "")
                if primer_h1:
                    st.markdown("**🔤 Primer H1:**")
                    st.success(primer_h1)
                
                # Mostrar estructura completa de headings
                estructura = url_result.get("estructura_completa", {})
                if estructura and estructura.get("headings"):
                    st.markdown("**📊 Estructura jerárquica completa:**")
                    
                    # Mostrar totales
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total H1", estructura.get("total_h1", 0))
                    with col2:
                        st.metric("Total H2", estructura.get("total_h2", 0))
                    with col3:
                        st.metric("Total H3", estructura.get("total_h3", 0))
                    
                    # Mostrar árbol de headings
                    for h1_item in estructura.get("headings", []):
                        # H1
                        st.markdown(f"### 🔹 {h1_item.get('titulo', '')}")
                        
                        # H2s bajo este H1
                        for h2_item in h1_item.get("h2", []):
                            st.markdown(f"#### &nbsp;&nbsp;&nbsp;&nbsp;↳ {h2_item.get('titulo', '')}")
                            
                            # H3s bajo este H2
                            for h3_item in h2_item.get("h3", []):
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;• {h3_item.get('titulo', '')}")
                
                # Compatibilidad con formato antiguo
                elif url_result.get("h1"):
                    h1_data = url_result.get("h1", {})
                    if h1_data and h1_data.get("titulo"):
                        # H1
                        st.markdown(f"### {h1_data['titulo']}")
                        
                        # H2s
                        for h2 in h1_data.get("h2", []):
                            st.markdown(f"#### ↳ {h2.get('titulo', '')}")
                            
                            # H3s
                            for h3 in h2.get("h3", []):
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {h3.get('titulo', '')}")
            
            st.divider()
