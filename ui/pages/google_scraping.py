"""
Página de UI para Scraping de Google
"""
import streamlit as st
import json
import asyncio
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay, SelectBox
from services.google_scraping_service import GoogleScrapingService
from services.tag_scraping_service import TagScrapingService
from services.drive_service import DriveService
from config import config
from repositories.mongo_repository import MongoRepository

class GoogleScrapingPage:
    """Página para scraping de resultados de Google"""
    
    def __init__(self):
        self.scraping_service = GoogleScrapingService()
        self.tag_service = TagScrapingService()
        self.drive_service = DriveService()
        # Importar la página de etiquetas para reutilizar su visualización
        from ui.pages.tag_scraping import TagScrapingPage
        self.tag_page = TagScrapingPage()
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "query_input" not in st.session_state:
            st.session_state.query_input = ""
        if "scraping_results" not in st.session_state:
            st.session_state.scraping_results = []
        # Estados para las configuraciones
        if "num_results" not in st.session_state:
            st.session_state.num_results = 30
        if "language_option" not in st.session_state:
            st.session_state.language_option = "Español (España)"
        if "domain_option" not in st.session_state:
            st.session_state.domain_option = "España (.es)"
        if "extract_tags" not in st.session_state:
            st.session_state.extract_tags = False
    
    def render(self):
        """Renderiza la página completa"""
        st.title(f"{config.ui.icons['search']} Scraping de URLs desde Google")
        
        # Sección de configuración
        self._render_configuration_section()
        
        # Botones de acción
        self._render_action_buttons()
        
        # Mostrar resultados si existen
        if st.session_state.scraping_results:
            self._render_results_section()
    
    def _render_configuration_section(self):
        """Renderiza la sección de configuración"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.session_state.query_input = st.text_area(
                "📝 Escribe una o más búsquedas separadas por coma o enter",
                st.session_state.query_input,
                height=400,
                placeholder="ej: mejores hoteles Madrid, restaurantes Barcelona"
            )
        
        with col2:
            # Número de resultados
            num_results = st.selectbox(
                "📄 Nº resultados",
                options=list(range(10, 101, 10)),
                index=list(range(10, 101, 10)).index(st.session_state.num_results)
            )
            st.session_state.num_results = num_results
            
            # Idioma y región
            language_option = st.selectbox(
                "🌐 Idioma y región",
                options=list(config.scraping.search_languages.keys()),
                index=list(config.scraping.search_languages.keys()).index(st.session_state.language_option)
            )
            st.session_state.language_option = language_option
            
            # Dominio de Google
            domain_option = st.selectbox(
                "🧭 Dominio de Google",
                options=list(config.scraping.google_domains.keys()),
                index=list(config.scraping.google_domains.keys()).index(st.session_state.domain_option)
            )
            st.session_state.domain_option = domain_option
    
    def _render_action_buttons(self):
        """Renderiza los botones de acción"""
        if st.session_state.scraping_results:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if Button.primary("Buscar", icon=config.ui.icons["search"]):
                    self._perform_search()
            
            with col2:
                if Button.secondary("Nueva Búsqueda", icon=config.ui.icons["clean"]):
                    self._clear_search()
            
            with col3:
                if Button.secondary("Exportar JSON", icon=config.ui.icons["download"]):
                    self._export_json()
            
            with col4:
                if Button.secondary("Exportar a MongoDB", icon="🧬"):
                    self._export_to_mongo()
            with col5:
                if Button.secondary("Subir a Drive", icon=config.ui.icons["upload"]):
                    self._upload_to_drive()
        else:
            col1, col2 = st.columns([1, 3])
            with col1:
                if Button.primary("Buscar", icon=config.ui.icons["search"]):
                    self._perform_search()
            with col2:
                # Checkbox para extraer etiquetas
                st.session_state.extract_tags = st.checkbox(
                    "🏷️ Extraer etiquetas HTML automáticamente",
                    value=st.session_state.extract_tags,
                    help="Extrae la estructura H1/H2/H3 de las URLs encontradas"
                )
    
    def _perform_search(self):
        """Ejecuta la búsqueda en Google y opcionalmente extrae etiquetas HTML"""
        if not st.session_state.query_input:
            Alert.warning("Por favor, introduce al menos una búsqueda")
            return
        
        # Parsear términos de búsqueda
        raw_input = st.session_state.query_input.replace("\n", ",")
        queries = [q.strip() for q in raw_input.split(",") if q.strip()]
        
        # Obtener configuraciones actuales
        language_code, region_code = config.scraping.search_languages[st.session_state.language_option]
        google_domain = config.scraping.google_domains[st.session_state.domain_option]
        
        with LoadingSpinner.show("Consultando BrightData SERP API..."):
            try:
                results = self.scraping_service.search_multiple_queries(
                    queries=queries,
                    num_results=st.session_state.num_results,
                    language_code=language_code,
                    region_code=region_code,
                    google_domain=google_domain
                )
                
                # Si el checkbox está marcado, extraer etiquetas HTML
                if st.session_state.extract_tags:
                    Alert.info("Extrayendo etiquetas HTML de las URLs encontradas...")
                    
                    # Contenedor para el progreso
                    progress_container = st.container()
                    
                    with progress_container:
                        # Ejecutar extracción de etiquetas
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        try:
                            tag_results = loop.run_until_complete(
                                self.tag_service.scrape_tags_from_json(
                                    results,
                                    max_concurrent=5,
                                    progress_callback=None
                                )
                            )
                            
                            # Actualizar los resultados con las etiquetas extraídas
                            st.session_state.scraping_results = tag_results
                            
                            # Contar URLs procesadas
                            total_urls = sum(len(r.get("resultados", [])) for r in tag_results)
                            Alert.success(f"✅ Se procesaron {total_urls} URLs con sus etiquetas HTML")
                            
                        finally:
                            loop.close()
                else:
                    # Solo guardar resultados de Google
                    st.session_state.scraping_results = results
                    Alert.success(f"Se encontraron resultados para {len(results)} búsquedas")
                
                st.rerun()
                
            except Exception as e:
                Alert.error(f"Error durante la búsqueda: {str(e)}")
    
    def _clear_search(self):
        """Limpia la búsqueda actual"""
        st.session_state.scraping_results = []
        st.session_state.query_input = ""
        st.rerun()
    
    def _export_json(self):
        """Exporta los resultados a JSON"""
        if not st.session_state.scraping_results:
            return
        
        filename = f"resultados_{st.session_state.query_input.replace(' ', '_').replace(',', '-')}.json"
        json_bytes = json.dumps(
            st.session_state.scraping_results, 
            ensure_ascii=False, 
            indent=2
        ).encode("utf-8")
        
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name=filename,
            mime="application/json"
        )
    
    def _upload_to_drive(self):
        """Sube los resultados a Google Drive"""
        if not st.session_state.get("proyecto_id"):
            Alert.warning("Por favor, selecciona un proyecto en la barra lateral")
            return
        
        filename = f"resultados_{st.session_state.query_input.replace(' ', '_').replace(',', '-')}.json"
        json_bytes = json.dumps(
            st.session_state.scraping_results, 
            ensure_ascii=False, 
            indent=2
        ).encode("utf-8")
        
        try:
            # Obtener o crear subcarpeta
            folder_id = self.drive_service.get_or_create_folder(
                "scraping google", 
                st.session_state.proyecto_id
            )
            
            # Subir archivo
            link = self.drive_service.upload_file(
                filename,
                json_bytes,
                folder_id
            )
            
            if link:
                Alert.success(f"Archivo subido correctamente: [Ver archivo]({link})")
            else:
                Alert.error("Error al subir el archivo")
                
        except Exception as e:
            Alert.error(f"Error al subir a Drive: {str(e)}")

    def _export_to_mongo(self):
        """Exporta los resultados a MongoDB"""
        try:
            mongo = MongoRepository(config.mongo_uri, config.app.mongo_default_db)
            
            # Determinar la colección según si se extrajeron etiquetas o no
            collection_name = "hoteles" if st.session_state.extract_tags else "URLs Google"
            
            inserted_ids = mongo.insert_many(
                documents=st.session_state.scraping_results,
                collection_name=collection_name
            )
            Alert.success(f"{len(inserted_ids)} JSON exportado a MongoDB (colección: {collection_name}):\n" + "\n".join(f"- {i}" for i in inserted_ids))
            return
        except Exception as e:
            Alert.error(f"Error exportando a MongoDB: {str(e)}")
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        Card.render(
            title="Resultados de Búsqueda",
            icon=config.ui.icons["document"],
            content=lambda: self._display_results()
        )
    
    def _display_results(self):
        """Muestra los resultados de búsqueda o etiquetas HTML según el modo"""
        # Si se extrajeron etiquetas, mostrar como en la página de etiquetas HTML
        if st.session_state.extract_tags and st.session_state.scraping_results and st.session_state.scraping_results[0].get('resultados'):
            st.subheader("📦 Resultados estructurados")
            
            # Resumen
            total_searches = len(st.session_state.scraping_results)
            total_urls = sum(len(r.get("resultados", [])) for r in st.session_state.scraping_results)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Búsquedas procesadas", total_searches)
            with col2:
                st.metric("URLs analizadas", total_urls)
            
            # Mostrar resultados por búsqueda
            for result in st.session_state.scraping_results:
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
        else:
            # Mostrar resultados normales de Google
            for result in st.session_state.scraping_results:
                with st.expander(f"🔍 {result['busqueda']} - {len(result.get('urls', []))} URLs"):
                    # Información de la búsqueda
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Idioma:** {result['idioma']}")
                    with col2:
                        st.write(f"**Región:** {result['region']}")
                    with col3:
                        st.write(f"**Dominio:** {result['dominio']}")
                    
                    # Mostrar URLs
                    if result.get('urls'):
                        st.write("**URLs encontradas:**")
                        for i, url in enumerate(result['urls'], 1):
                            st.write(f"{i}. {url}")
                    else:
                        st.write("No se encontraron URLs")
                    
                    # Mostrar error si existe
                    if result.get('error'):
                        Alert.error(f"Error: {result['error']}")
        
        # Mostrar JSON completo
        DataDisplay.json(
            st.session_state.scraping_results,
            title="JSON Completo",
            expanded=True
        )
    
    def _display_url_result(self, url_result: Dict[str, Any]):
        """Reutiliza el método de visualización de la página de etiquetas HTML"""
        # Usar directamente el método de la página de etiquetas
        self.tag_page._display_url_result(url_result)
