"""
Página de UI para Scraping de Etiquetas HTML
"""
import streamlit as st
import json
import asyncio
from typing import Dict, Any, Optional
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.tag_scraping_service import TagScrapingService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
from config import config

class TagScrapingPage:
    """Página para extraer estructura jerárquica de etiquetas HTML"""
    
    def __init__(self):
        self.tag_service = TagScrapingService()
        self.drive_service = DriveService()
        self.mongo_repo = MongoRepository(
            uri=st.secrets["mongodb"]["uri"],
            db_name=st.secrets["mongodb"]["db"]
        )
        self._init_session_state()
    
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
    
    def render(self):
        """Renderiza la página completa"""
        st.title("🏷️ Scraping de Etiquetas HTML")
        st.markdown("### 📁 Extrae estructura jerárquica (h1 → h2 → h3) desde archivo JSON")
        
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
            ["Desde Drive", "Desde ordenador"],
            horizontal=True,
            index=0
        )
        
        if source == "Desde ordenador":
            self._handle_file_upload()
        else:
            self._handle_drive_selection()
    
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
    
    def _render_processing_section(self):
        """Renderiza la sección de procesamiento"""
        # Mostrar preview del JSON
        try:
            json_data = json.loads(st.session_state.json_content)
            
            with st.expander("📄 Vista previa del JSON cargado", expanded=True):
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
        # Contador de progreso
        progress_container = st.empty()
        
        def update_progress(message: str):
            progress_container.info(message)
        
        with LoadingSpinner.show("Extrayendo estructura de etiquetas..."):
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
                Alert.success(f"Se procesaron {total_urls} URLs exitosamente")
                
                progress_container.empty()
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
            expanded=False
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
                st.markdown(f"✅ **{url}** - Status: {status}")
            
            # Mostrar estructura de encabezados si existe
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
