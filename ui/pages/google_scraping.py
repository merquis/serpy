"""
Página de UI para Scraping de Google
"""
import streamlit as st
import json
from typing import List
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay, SelectBox
from services.scraping_service import GoogleScrapingService
from services.drive_service import DriveService
from config import config

class GoogleScrapingPage:
    """Página para scraping de resultados de Google"""
    
    def __init__(self):
        self.scraping_service = GoogleScrapingService()
        self.drive_service = DriveService()
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "query_input" not in st.session_state:
            st.session_state.query_input = ""
        if "scraping_results" not in st.session_state:
            st.session_state.scraping_results = []
        # Estados para las configuraciones
        if "num_results" not in st.session_state:
            st.session_state.num_results = 10
        if "language_option" not in st.session_state:
            st.session_state.language_option = "Español (España)"
        if "domain_option" not in st.session_state:
            st.session_state.domain_option = "España (.es)"
    
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
                "📝 Escribe una o más búsquedas separadas por coma",
                st.session_state.query_input,
                height=100,
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
            col1, col2, col3, col4 = st.columns(4)
            
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
                if Button.secondary("Subir a Drive", icon=config.ui.icons["upload"]):
                    self._upload_to_drive()
        else:
            col1, _ = st.columns([1, 3])
            with col1:
                if Button.primary("Buscar", icon=config.ui.icons["search"]):
                    self._perform_search()
    
    def _perform_search(self):
        """Ejecuta la búsqueda en Google"""
        if not st.session_state.query_input:
            Alert.warning("Por favor, introduce al menos una búsqueda")
            return
        
        # Parsear términos de búsqueda
        queries = [q.strip() for q in st.session_state.query_input.split(",") if q.strip()]
        
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
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        Card.render(
            title="Resultados de Búsqueda",
            icon=config.ui.icons["document"],
            content=lambda: self._display_results()
        )
    
    def _display_results(self):
        """Muestra los resultados de búsqueda"""
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
            expanded=False
        ) 