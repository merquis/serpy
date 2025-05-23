import streamlit as st
import json
import asyncio
from typing import Dict, Any, Optional

# --- Bloque de Mocks e Imports ---
class MockCommon:
    def __call__(self, *args, **kwargs): pass
    def success(self, msg): st.success(msg)
    def error(self, msg): st.error(msg)
    def info(self, msg): st.info(msg)
    def primary(self, label, icon=""): return st.button(label)
    def secondary(self, label, icon=""): return st.button(label)
    def show(self, label): return st.spinner(label)
    def json(self, data, title="", expanded=False): st.json(data, expanded=expanded)
    def render(self, title, description, icon, action_label, action_callback):
        st.warning(title); st.write(description)
        if st.button(action_label): action_callback()

try: from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay, EmptyState
except ImportError:
    st.warning("Componentes comunes (ui.components.common) no encontrados, usando Mocks.")
    Card, Alert, Button, LoadingSpinner, DataDisplay, EmptyState = [type(f"Mock{name}", (MockCommon,), {})() for name in ["Card", "Alert", "Button", "LoadingSpinner", "DataDisplay", "EmptyState"]]

try: from services.drive_service import DriveService
except ImportError: st.warning("DriveService no encontrado, usando Mock."); DriveService = None
try: from repositories.mongo_repository import MongoRepository
except ImportError: st.warning("MongoRepository no encontrado, usando Mock."); MongoRepository = None
try: from config import config
except ImportError:
    st.warning("config.py no encontrado, usando MockConfig.")
    class MockConfigModule:
        class UiConfig: icons = {"download": "⬇️", "upload": "⬆️", "clean": "🧹"}
        ui = UiConfig()
    config = MockConfigModule()
# --- Fin Bloque de Mocks e Imports ---

from services.tag_scraping_service import TagScrapingService

class TagScrapingPage:
    def __init__(self):
        self.tag_service = TagScrapingService()
        self.drive_service = DriveService() if DriveService else type('DriveServiceMock', (), {'get_or_create_folder': lambda s,fn,pid: 'mock_folder_id', 'list_json_files_in_folder': lambda s,fid: {'mock_drive_file.json': 'mock_file_id'}, 'get_file_content': lambda s,fid: b'[]', 'upload_file': lambda s,fn,cb,fid: 'http://mock.link/file'})()
        
        if MongoRepository:
            try:
                self.mongo_repo = MongoRepository(uri=st.secrets["mongodb"]["uri"], db_name=st.secrets["mongodb"]["db"])
                st.toast("MongoRepository inicializado.", icon="📄")
            except KeyError:
                st.error("Secretos MongoDB (uri/db) no encontrados. Usando Mock.")
                self.mongo_repo = type('MongoRepoMock', (), {'insert_many': lambda s,d,cn: [f'mock_id_{i}' for i in range(len(d or []))], 'insert_one': lambda s,d,cn: 'mock_id_1'})()
            except Exception as e_mongo:
                st.error(f"Error inicializando MongoRepository: {e_mongo}. Usando Mock.")
                self.mongo_repo = type('MongoRepoMock', (), {'insert_many': lambda s,d,cn: [f'mock_id_{i}' for i in range(len(d or []))], 'insert_one': lambda s,d,cn: 'mock_id_1'})()
        else:
            st.warning("MongoRepository no importado. Usando Mock.")
            self.mongo_repo = type('MongoRepoMock', (), {'insert_many': lambda s,d,cn: [f'mock_id_{i}' for i in range(len(d or []))], 'insert_one': lambda s,d,cn: 'mock_id_1'})()
        
        self._init_session_state()

    def _init_session_state(self):
        prefix = "tag_pg_"
        defaults = {
            f"{prefix}json_content": None, f"{prefix}json_filename": None,
            f"{prefix}tag_results": None, f"{prefix}export_filename": "etiquetas_jerarquicas.json",
            f"{prefix}scraping_stats": None
        }
        for key, value in defaults.items():
            if key not in st.session_state: st.session_state[key] = value

    def render(self):
        st.title("🏷️ Scraping de Etiquetas HTML")
        st.markdown("### 📁 Extrae estructura jerárquica (h1 → h2 → h3) desde archivo JSON")
        self._render_source_selector()
        if st.session_state.tag_pg_json_content and not st.session_state.tag_pg_tag_results:
            self._render_processing_section()
        if st.session_state.tag_pg_tag_results:
            self._render_results_section()

    def _render_source_selector(self):
        source = st.radio("Selecciona fuente:", ["Desde Drive", "Desde ordenador"], horizontal=True, key="tag_source_radio")
        if source == "Desde ordenador": self._handle_file_upload()
        else: self._handle_drive_selection()

    def _handle_file_upload(self):
        uploaded_file = st.file_uploader("Sube archivo JSON", type=["json"], key="tag_file_uploader")
        if uploaded_file:
            st.session_state.tag_pg_json_content = uploaded_file.read()
            st.session_state.tag_pg_json_filename = uploaded_file.name
            st.session_state.tag_pg_tag_results = None
            st.session_state.tag_pg_scraping_stats = None
            Alert.success(f"Archivo {uploaded_file.name} cargado")

    def _handle_drive_selection(self):
        if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
            Alert.error("Selecciona primero un proyecto en la barra lateral")
            return
        try:
            folder_id = self.drive_service.get_or_create_folder("scraping google", st.session_state.proyecto_id)
            files = self.drive_service.list_json_files_in_folder(folder_id)
            if not files:
                Alert.warning("No hay archivos JSON en la carpeta 'scraping google' del proyecto en Drive.")
                return
            file_names = list(files.keys())
            selected_file = st.selectbox("Selecciona un archivo de Drive", file_names, key="tag_drive_selectbox")
            if Button.primary("Cargar archivo de Drive", icon=config.ui.icons.get("download", "⬇️")): # Usar .get
                content = self.drive_service.get_file_content(files[selected_file])
                st.session_state.tag_pg_json_content = content
                st.session_state.tag_pg_json_filename = selected_file
                st.session_state.tag_pg_tag_results = None
                st.session_state.tag_pg_scraping_stats = None
                Alert.success(f"Archivo {selected_file} cargado desde Drive")
        except Exception as e: Alert.error(f"Error al acceder a Drive: {str(e)}")

    def _render_processing_section(self):
        try:
            json_data = json.loads(st.session_state.tag_pg_json_content)
            with st.expander("📄 Vista previa del JSON cargado", expanded=False): st.json(json_data)
            max_concurrent = st.slider("🔁 Concurrencia máxima", 1, 10, 5, help="URLs procesadas simultáneamente", key="tag_concurrency_slider")
            st.info("💡 **Estrategia:** httpx (rápido) -> Playwright (robusto)")
            if Button.primary("Extraer estructura de etiquetas", icon="🔄"):
                self._process_urls(json_data, max_concurrent)
        except json.JSONDecodeError as e: Alert.error(f"Error al decodificar JSON: {str(e)}")

    def _process_urls(self, json_data: Any, max_concurrent: int):
        progress_container = st.empty()
        status_messages = []
        def update_progress(message: str):
            status_messages.append(message)
            with progress_container.container(): # Usar container para el spinner + texto
                st.info(status_messages[-1] if status_messages else "Iniciando...")
                with st.expander("Historial reciente", expanded=False):
                    for msg in status_messages[-5:]: st.caption(msg)

        with LoadingSpinner.show("Iniciando extracción de etiquetas..."): # Usar Mock si es necesario
            try:
                update_progress(f"🚀 Iniciando con concurrencia: {max_concurrent}")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    self.tag_service.scrape_tags_from_json(json_data, max_concurrent, update_progress)
                )
                loop.close()
                st.session_state.tag_pg_tag_results = results
                st.session_state.tag_pg_scraping_stats = {
                    "httpx_success": self.tag_service.successful_httpx_count,
                    "playwright_fallback": self.tag_service.playwright_fallback_count,
                    "total": self.tag_service.successful_httpx_count + self.tag_service.playwright_fallback_count
                }
                base_name = st.session_state.tag_pg_json_filename or "etiquetas"
                st.session_state.tag_pg_export_filename = base_name.replace(".json", "") + "_TAGS.json"
                total_urls_processed = sum(len(r.get("resultados", [])) for r in results if isinstance(r, dict))
                progress_container.empty() 
                Alert.success(f"✅ {total_urls_processed} URLs procesadas para etiquetas.")
                st.rerun()
            except Exception as e: Alert.error(f"Error durante procesamiento de etiquetas: {str(e)}"); st.exception(e)

    def _render_results_section(self):
        results = st.session_state.tag_pg_tag_results
        if st.session_state.tag_pg_scraping_stats: self._render_scraping_stats()
        st.session_state.tag_pg_export_filename = st.text_input("📄 Nombre para exportar JSON", value=st.session_state.tag_pg_export_filename, key="tag_export_filename_input")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1: self._render_download_button()
        with col2: self._render_drive_upload_button()
        with col3: self._render_mongodb_upload_button()
        with col4:
            if Button.secondary("Nueva extracción de Tags", icon=config.ui.icons.get("clean", "🧹")): # Usar .get
                self._clear_results()
        
        self._display_results(results)

    def _render_scraping_stats(self):
        stats = st.session_state.tag_pg_scraping_stats
        st.markdown("### 📊 Estadísticas de Scraping (Etiquetas)")
        col1, col2, col3, col4 = st.columns(4)
        total = stats.get("total", 0)
        httpx_s = stats.get("httpx_success", 0)
        playwright_f = stats.get("playwright_fallback", 0)
        with col1: st.metric("Total URLs procesadas", total)
        with col2: st.metric("httpx (rápido)", httpx_s, f"{(httpx_s/total*100):.1f}%" if total > 0 else "0%")
        with col3: st.metric("Playwright (robusto)", playwright_f, f"{(playwright_f/total*100):.1f}%" if total > 0 else "0%")
        
        total_time = sum(r_item.get("scraping_time", 0) for res_group in st.session_state.tag_pg_tag_results if isinstance(res_group, dict) for r_item in res_group.get("resultados", []))
        avg_time = total_time / total if total > 0 else 0
        with col4: st.metric("Tiempo promedio/URL", f"{avg_time:.2f}s")
        st.divider()

    def _prepare_results_for_json(self, data):
        if isinstance(data, dict): return {k: self._prepare_results_for_json(v) for k, v in data.items()}
        elif isinstance(data, list): return [self._prepare_results_for_json(item) for item in data]
        elif hasattr(data, '__str__') and type(data).__name__ == 'ObjectId': return str(data) # Para BSON ObjectId de Mongo
        return data

    def _render_download_button(self):
        results_for_json = self._prepare_results_for_json(st.session_state.tag_pg_tag_results)
        json_bytes = json.dumps(results_for_json, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(label="⬇️ Descargar JSON (Tags)", data=json_bytes, file_name=st.session_state.tag_pg_export_filename, mime="application/json")

    def _render_drive_upload_button(self):
        if Button.secondary("Subir Tags a Drive", icon=config.ui.icons.get("upload", "⬆️")):
            if "proyecto_id" not in st.session_state or not st.session_state.proyecto_id:
                Alert.warning("Selecciona un proyecto en la barra lateral.")
                return
            try:
                results_for_json = self._prepare_results_for_json(st.session_state.tag_pg_tag_results)
                json_bytes = json.dumps(results_for_json, ensure_ascii=False, indent=2).encode("utf-8")
                folder_id = self.drive_service.get_or_create_folder("scraping etiquetas html", st.session_state.proyecto_id)
                link = self.drive_service.upload_file(st.session_state.tag_pg_export_filename, json_bytes, folder_id)
                if link: Alert.success(f"Archivo de Tags subido: [Ver en Drive]({link})")
                else: Alert.error("Error al subir archivo de Tags a Drive")
            except Exception as e: Alert.error(f"Error al subir Tags a Drive: {str(e)}")

    def _render_mongodb_upload_button(self):
        if Button.secondary("Subir Tags a MongoDB", icon="📤"):
            try:
                data = st.session_state.tag_pg_tag_results
                collection_name = "scraped_tags" # O el nombre que prefieras
                if isinstance(data, list) and data:
                    if len(data) > 1 or isinstance(data[0], list): # Si es lista de listas de resultados o similar
                        docs_to_insert = []
                        for item_group in data:
                            if isinstance(item_group, dict) and "resultados" in item_group:
                                docs_to_insert.extend(item_group["resultados"])
                            elif isinstance(item_group, list): # Si ya es una lista de resultados
                                docs_to_insert.extend(item_group)
                        if docs_to_insert:
                             inserted_ids = self.mongo_repo.insert_many(docs_to_insert, collection_name)
                             Alert.success(f"Subidos {len(inserted_ids)} documentos de Tags a MongoDB.")
                        else: Alert.warning("No hay datos de resultados de tags para subir.")
                    elif isinstance(data[0], dict): # Lista de un solo grupo de resultados
                        docs_to_insert = data[0].get("resultados", [])
                        if docs_to_insert:
                            inserted_ids = self.mongo_repo.insert_many(docs_to_insert, collection_name)
                            Alert.success(f"Subidos {len(inserted_ids)} documentos de Tags a MongoDB.")
                        else: Alert.warning("No hay datos de resultados de tags para subir.")
                else: Alert.warning("No hay resultados de Tags para subir a MongoDB.")
            except Exception as e: Alert.error(f"Error al subir Tags a MongoDB: {str(e)}"); st.exception(e)

    def _clear_results(self):
        st.session_state.tag_pg_json_content = None
        st.session_state.tag_pg_json_filename = None
        st.session_state.tag_pg_tag_results = None
        st.session_state.tag_pg_export_filename = "etiquetas_jerarquicas.json"
        st.session_state.tag_pg_scraping_stats = None
        st.rerun()

    def _display_results(self, results: list):
        st.subheader("📦 Resultados de Etiquetas Estructurados")
        if not results: st.info("No hay resultados de etiquetas para mostrar."); return

        total_searches = len(results)
        total_urls_tags = sum(len(r.get("resultados", [])) for r in results if isinstance(r, dict))
        col1, col2 = st.columns(2)
        with col1: st.metric("Grupos de Búsqueda", total_searches)
        with col2: st.metric("URLs con Tags Analizadas", total_urls_tags)

        for result_group in results:
            if not isinstance(result_group, dict): continue
            search_term = result_group.get("busqueda", "N/A")
            urls_count = len(result_group.get("resultados", []))
            with st.expander(f"🔍 {search_term} (Etiquetas) - {urls_count} URLs"):
                cols_context = st.columns(3)
                with cols_context[0]: st.write(f"**Idioma:** {result_group.get('idioma', 'N/A')}")
                with cols_context[1]: st.write(f"**Región:** {result_group.get('region', 'N/A')}")
                with cols_context[2]: st.write(f"**Dominio:** {result_group.get('dominio', 'N/A')}")
                for url_result in result_group.get("resultados", []):
                    if isinstance(url_result, dict): self._display_url_result(url_result)
        
        DataDisplay.json(results, title="JSON Completo de Tags", expanded=False) # Usar Mock si es necesario

    def _display_url_result(self, url_result: Dict[str, Any]):
        url = url_result.get("url", "")
        status = url_result.get("status_code", "N/A")
        method = url_result.get("method", "unknown")
        scraping_time = url_result.get("scraping_time", 0)
        
        with st.container():
            col1_disp, col2_disp = st.columns([3,1])
            with col1_disp:
                if status == "error" or "error" in url_result: st.markdown(f"❌ **{url}**"); st.caption(f"Error: {url_result.get('error', 'Desconocido')}")
                else: st.markdown(f"✅ **{url}**")
            with col2_disp:
                method_emoji = "🚀" if method == "httpx" else "🤖" if "playwright" in method else "❓"
                st.caption(f"{method_emoji} {method} | ⏱️ {scraping_time:.2f}s")
            
            h1_data = url_result.get("h1", {})
            if h1_data and h1_data.get("titulo"):
                st.markdown(f"### {h1_data['titulo']}")
                for h2 in h1_data.get("h2", []):
                    st.markdown(f"#### ↳ {h2.get('titulo', '')}")
                    for h3 in h2.get("h3", []): st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {h3.get('titulo', '')}")
            elif status != "error" and "error" not in url_result : st.caption("⚠️ No se encontró H1.")
            st.divider()
