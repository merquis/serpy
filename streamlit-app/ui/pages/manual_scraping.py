"""
Página de UI para Scraping Manual de URLs
"""
import streamlit as st
import json
from typing import List, Dict, Any
from ui.components.common import Card, Alert, Button, LoadingSpinner, ProgressBar, DataDisplay
from services.manual_scraping_service import ManualScrapingService
from services.drive_service import DriveService
from config import config

class ManualScrapingPage:
    """Página para scraping manual de URLs"""
    
    def __init__(self):
        self.scraping_service = ManualScrapingService()
        self.drive_service = DriveService()
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "scraping_results" not in st.session_state:
            st.session_state.scraping_results = None
        if "selected_tags" not in st.session_state:
            st.session_state.selected_tags = ["title", "description", "h1", "h2", "h3"]
    
    def render(self):
        """Renderiza la página completa"""
        st.title("✋ Scraping Manual de URLs")
        st.markdown("### 🔗 Extrae etiquetas SEO de URLs que introduzcas manualmente")
        
        # Sección de entrada de URLs
        self._render_url_input_section()
        
        # Sección de selección de etiquetas
        self._render_tag_selection_section()
        
        # Sección de configuración avanzada
        self._render_advanced_settings()
        
        # Botón de ejecución
        self._render_execution_section()
        
        # Mostrar resultados si existen
        if st.session_state.scraping_results:
            self._render_results_section()
    
    def _render_url_input_section(self):
        """Renderiza la sección de entrada de URLs"""
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
            valid_urls, invalid_urls = self.scraping_service.validate_urls(raw_urls)
            
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
        else:
            st.info("ℹ️ Introduce al menos una URL para comenzar")
            st.session_state.valid_urls = []
    
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
    
    def _render_execution_section(self):
        """Renderiza la sección de ejecución"""
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
            self._execute_scraping()
    
    def _execute_scraping(self):
        """Ejecuta el proceso de scraping"""
        urls = st.session_state.valid_urls
        tags = st.session_state.selected_tags
        max_workers = st.session_state.get("max_workers", 5)
        timeout = st.session_state.get("timeout", 20)
        
        # Contenedor para el progreso
        progress_container = st.container()
        
        with LoadingSpinner.show(f"Analizando {len(urls)} URLs..."):
            try:
                # Ejecutar scraping
                results = self.scraping_service.scrape_urls(
                    urls=urls,
                    tags=tags,
                    max_workers=max_workers,
                    timeout=timeout
                )
                
                # Guardar resultados
                st.session_state.scraping_results = results
                
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
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        st.markdown("---")
        st.markdown("### 📦 Resultados Obtenidos")
        
        results = st.session_state.scraping_results
        
        # Estadísticas generales
        self._render_statistics(results)
        
        # Tabs para diferentes vistas
        tab1, tab2, tab3 = st.tabs(["📊 Vista General", "📄 Detalle por URL", "💾 JSON Completo"])
        
        with tab1:
            self._render_overview(results)
        
        with tab2:
            self._render_detailed_view(results)
        
        with tab3:
            self._render_json_view(results)
        
        # Opciones de exportación
        self._render_export_options(results)
    
    def _render_statistics(self, results: List[Dict]):
        """Renderiza estadísticas de los resultados"""
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
    
    def _render_overview(self, results: List[Dict]):
        """Renderiza vista general de resultados"""
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
    
    def _render_detailed_view(self, results: List[Dict]):
        """Renderiza vista detallada por URL"""
        url_options = [r["url"] for r in results]
        selected_url = st.selectbox("Selecciona una URL:", url_options)
        
        if selected_url:
            result = next(r for r in results if r["url"] == selected_url)
            
            if result.get("status_code") == 200:
                for tag in st.session_state.selected_tags:
                    if tag in result:
                        Card.render(
                            title=f"🏷️ {tag}",
                            content=lambda value=result[tag]: self._display_tag_value(value),
                            expandable=True,
                            expanded=False
                        )
            else:
                Alert.error(f"Error al procesar esta URL: {result.get('error', 'Desconocido')}")
    
    def _display_tag_value(self, value):
        """Muestra el valor de una etiqueta de forma apropiada"""
        if isinstance(value, list):
            if value:
                for item in value:
                    st.write(f"• {item}")
            else:
                st.caption("(lista vacía)")
        else:
            st.write(value or "(vacío)")
    
    def _render_json_view(self, results: List[Dict]):
        """Renderiza vista JSON completa"""
        DataDisplay.json(results, expanded=False)
    
    def _render_export_options(self, results: List[Dict]):
        """Renderiza opciones de exportación"""
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
                self._upload_to_drive(results)
        
        with col3:
            # Nueva extracción
            if Button.secondary("🔄 Nueva extracción", icon="🔄"):
                st.session_state.scraping_results = None
                st.rerun()
    
    def _upload_to_drive(self, results: List[Dict]):
        """Sube los resultados a Google Drive"""
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