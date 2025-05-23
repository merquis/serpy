import streamlit as st
import json
import asyncio
from typing import Dict, Any, Optional
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay
from services.tag_scraping_service import TagScrapingService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
# from config import config # Asegúrate de que config existe

# Placeholder para config si no lo tienes listo
class MockConfig:
    def __init__(self):
        self.ui = type('ui', (), {})()
        self.ui.icons = {"download": "⬇️", "upload": "⬆️", "clean": "🧹"}
config = MockConfig() # Usa esto si no tienes config.py


class TagScrapingPage:
    """Página para extraer estructura jerárquica de etiquetas HTML"""

    def __init__(self):
        self.tag_service = TagScrapingService()
        # Mock services if not available
        self.drive_service = type('DriveService', (), {'get_or_create_folder': lambda s,x,y: 'folder_id_mock', 'list_json_files_in_folder': lambda s,x: {'mock_file.json': 'file_id_mock'}, 'get_file_content': lambda s,x: b'{}', 'upload_file': lambda s,x,y,z: 'http://mock.link'})()
        self.mongo_repo = type('MongoRepo', (), {'insert_many': lambda s,x,y: ['id1', 'id2'], 'insert_one': lambda s,x,y: 'id1'})()
        # self.drive_service = DriveService()
        # self.mongo_repo = MongoRepository(
        #     uri=st.secrets["mongodb"]["uri"],
        #     db_name=st.secrets["mongodb"]["db"]
        # )
        self._init_session_state()

    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        defaults = {"json_content": None, "json_filename": None, "tag_results": None,
                    "export_filename": "etiquetas_jerarquicas.json", "scraping_stats": None}
        for key, value in defaults.items():
            if key not in st.session_state: st.session_state[key] = value

    def render(self):
        st.title("🏷️ Scraping de Etiquetas HTML")
        st.markdown("### 📁 Extrae estructura jerárquica (h1 → h2 → h3) desde archivo JSON")
        self._render_source_selector()
        if st.session_state.json_content and not st.session_state.tag_results: self._render_processing_section()
        if st.session_state.tag_results: self._render_results_section()

    def _render_source_selector(self):
        source = st.radio("Selecciona fuente:", ["Desde Drive", "Desde ordenador"], horizontal=True)
        if source == "Desde ordenador": self._handle_file_upload()
        else: self._handle_drive_selection()

    def _handle_file_upload(self):
        uploaded_file = st.file_uploader("Sube archivo JSON", type=["json"])
        if uploaded_file:
            st.session_state.json_content = uploaded_file.read()
            st.session_state.json_filename = uploaded_file.name
            st.session_state.tag_results = None
            st.session_state.scraping_stats = None
            st.success(f"Archivo {uploaded_file.name} cargado")

    def _handle_drive_selection(self):
        if "proyecto_id" not in st.session_state:
            st.error("Selecciona primero un proyecto")
            return
        try:
            folder_id = self.drive_service.get_or_create_folder("scraping google", st.session_state.proyecto_id)
            files = self.drive_service.list_json_files_in_folder(folder_id)
            if not files:
                st.warning("No hay archivos JSON")
                return
            selected_file = st.selectbox("Selecciona un archivo", list(files.keys()))
            if st.button("Cargar archivo de Drive"):
                content = self.drive_service.get_file_content(files[selected_file])
                st.session_state.json_content = content
                st.session_state.json_filename = selected_file
                st.session_state.tag_results = None
                st.session_state.scraping_stats = None
                st.success(f"Archivo {selected_file} cargado")
        except Exception as e:
            st.error(f"Error al acceder a Drive: {str(e)}")

    def _render_processing_section(self):
        try:
            json_data = json.loads(st.session_state.json_content)
            with st.expander("📄 Vista previa", expanded=False): st.json(json_data)
            max_concurrent = st.slider("🔁 Concurrencia", 1, 10, 5)
            st.info("💡 Estrategia: httpx (rápido) -> Playwright (robusto)")
            if st.button("Extraer estructura", type="primary"):
                self._process_urls(json_data, max_concurrent)
        except json.JSONDecodeError as e:
            st.error(f"Error JSON: {str(e)}")

    def _process_urls(self, json_data: Any, max_concurrent: int):
        progress_container = st.empty()
        progress_messages = []

        def update_progress(message: str):
            progress_messages.append(message)
            with progress_container.container():
                st.info(progress_messages[-1])
                with st.expander("Historial", expanded=False):
                    for msg in progress_messages[-5:]: st.caption(msg)

        with st.spinner("Iniciando extracción..."):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    self.tag_service.scrape_tags_from_json(
                        json_data, max_concurrent=max_concurrent, progress_callback=update_progress
                    )
                )
                st.session_state.tag_results = results
                st.session_state.scraping_stats = {
                    "httpx_success": self.tag_service.successful_httpx_count,
                    "playwright_fallback": self.tag_service.playwright_fallback_count,
                    "total": self.tag_service.successful_httpx_count + self.tag_service.playwright_fallback_count
                }
                base_name = st.session_state.json_filename or "etiquetas"
                st.session_state.export_filename = base_name.replace(".json", "_ALL.json")
                total_urls = sum(len(r.get("resultados", [])) for r in results)
                progress_container.empty()
                st.success(f"✅ Se procesaron {total_urls} URLs")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                loop.close()

    def _render_results_section(self):
        results = st.session_state.tag_results
        if st.session_state.scraping_stats: self._render_scraping_stats()
        st.session_state.export_filename = st.text_input("📄 Nombre para exportar", value=st.session_state.export_filename)
        col1, col2, col3, col4 = st.columns(4)
        with col1: self._render_download_button()
        with col2: self._render_drive_upload_button()
        with col3: self
