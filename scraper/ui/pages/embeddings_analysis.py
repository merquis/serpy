"""
Página de UI para Análisis de Embeddings
"""
import streamlit as st
import json
from typing import Dict, Any, Optional
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay, SelectBox
from services.embeddings_service import EmbeddingsService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
from config import settings

class EmbeddingsAnalysisPage:
    """Página para análisis semántico con embeddings"""
    
    def __init__(self):
        self.embeddings_service = EmbeddingsService()
        self.drive_service = DriveService()
        self.mongo_repo = MongoRepository(
            uri=st.secrets["mongodb"]["uri"],
            db_name=st.secrets["mongodb"]["db"]
        )
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "json_data" not in st.session_state:
            st.session_state.json_data = None
        if "analysis_result" not in st.session_state:
            st.session_state.analysis_result = None
    
    def render(self):
        """Renderiza la página completa"""
        st.title("📊 Análisis Semántico con Embeddings")
        st.markdown("### 🔍 Agrupación semántica y generación de árbol SEO")
        
        # Sección de carga de datos
        self._render_data_source_section()
        
        # Sección de parámetros de agrupación
        self._render_clustering_parameters()
        
        # Botón de ejecución
        self._render_execution_section()
        
        # Mostrar resultados si existen
        if st.session_state.analysis_result:
            self._render_results_section()
    
    def _render_data_source_section(self):
        """Renderiza la sección de carga de datos"""
        st.markdown("#### 📁 Fuente de Datos")
        
        source = st.radio(
            "Selecciona fuente del archivo:",
            ["Desde Drive", "Desde ordenador", "Desde MongoDB"],
            horizontal=True
        )
        
        if source == "Desde ordenador":
            self._handle_file_upload()
        elif source == "Desde Drive":
            self._handle_drive_source()
        elif source == "Desde MongoDB":
            self._handle_mongodb_source()
        
        # Mostrar estado de carga
        if st.session_state.json_data:
            keyword = self.embeddings_service.get_extracted_keyword(st.session_state.json_data)
            if keyword:
                Alert.success(f"Datos cargados - Keyword: {keyword}")
            else:
                Alert.success("Datos cargados correctamente")
    
    def _handle_file_upload(self):
        """Maneja la carga de archivo desde el ordenador"""
        uploaded_file = st.file_uploader("📁 Sube un archivo JSON", type=["json"])
        
        if uploaded_file:
            try:
                st.session_state.json_data = uploaded_file.read()
                Alert.success(f"✅ Archivo {uploaded_file.name} cargado correctamente")
                st.rerun()
            except Exception as e:
                Alert.error(f"Error al cargar archivo: {str(e)}")
    
    def _handle_drive_source(self):
        """Maneja la carga desde Google Drive"""
        if "proyecto_id" not in st.session_state:
            Alert.warning("⚠️ Selecciona primero un proyecto en la barra lateral.")
            return
        
        try:
            folder_id = self.drive_service.get_or_create_folder(
                "scraper etiquetas google",
                st.session_state.proyecto_id
            )
            
            files = self.drive_service.list_json_files_in_folder(folder_id)
            
            if files:
                selected_file = st.selectbox("Selecciona archivo JSON:", list(files.keys()))
                
                if Button.primary("📂 Cargar archivo de Drive", icon="📥"):
                    content = self.drive_service.get_file_content(files[selected_file])
                    st.session_state.json_data = content
                    Alert.success(f"✅ Archivo {selected_file} cargado desde Drive")
                    st.rerun()
            else:
                Alert.warning("⚠️ No hay archivos JSON en esa carpeta")
                
        except Exception as e:
            Alert.error(f"Error al acceder a Drive: {str(e)}")
    
    def _handle_mongodb_source(self):
        """Maneja la carga desde MongoDB"""
        try:
            # Obtener documentos con campo 'busqueda'
            documents = self.mongo_repo.find_many(
                {},
                collection_name="hoteles",
                limit=100
            )
            
            # Filtrar documentos con campo busqueda
            docs_with_search = [
                doc for doc in documents 
                if doc.get("busqueda")
            ]
            
            if docs_with_search:
                # Crear opciones para el selector
                options = {
                    f"{doc.get('busqueda', 'Sin búsqueda')} - {doc.get('_id', '')}": doc
                    for doc in docs_with_search
                }
                
                selected_key = st.selectbox("Selecciona búsqueda:", list(options.keys()))
                
                if Button.primary("📂 Cargar desde MongoDB", icon="📥"):
                    selected_doc = options[selected_key]
                    st.session_state.json_data = json.dumps(selected_doc).encode()
                    Alert.success(f"✅ Documento MongoDB cargado: {selected_key}")
                    st.rerun()
            else:
                Alert.warning("⚠️ No hay documentos con campo 'busqueda' en MongoDB")
                
        except Exception as e:
            Alert.error(f"Error al acceder a MongoDB: {str(e)}")
    
    def _render_clustering_parameters(self):
        """Renderiza los parámetros de agrupación"""
        st.markdown("---")
        st.markdown("#### ⚙️ Parámetros de Agrupación")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.n_clusters_h2 = st.slider(
                "🧠 Número de clústeres para H2",
                min_value=2,
                max_value=30,
                value=10,
                help="Número de grupos para agrupar títulos H2"
            )
            
            st.session_state.max_titles_h2 = st.slider(
                "📄 Máximo de títulos H2",
                min_value=100,
                max_value=1500,
                value=300,
                help="Máximo número de títulos H2 a procesar"
            )
        
        with col2:
            st.session_state.n_clusters_h3 = st.slider(
                "🧠 Número de clústeres para H3",
                min_value=2,
                max_value=100,
                value=30,
                help="Número de grupos para agrupar títulos H3"
            )
            
            st.session_state.max_titles_h3 = st.slider(
                "📄 Máximo de títulos H3",
                min_value=100,
                max_value=3000,
                value=900,
                help="Máximo número de títulos H3 a procesar"
            )
        
        # Modelo GPT
        st.markdown("#### 🤖 Modelo de IA")
        st.session_state.model = st.selectbox(
            "Modelo GPT",
            settings.gpt_models,
            index=settings.gpt_models.index("chatgpt-4o-latest") if "chatgpt-4o-latest" in settings.gpt_models else 0,
            help="Modelo de IA para generar títulos representativos"
        )
    
    def _render_execution_section(self):
        """Renderiza la sección de ejecución"""
        if Button.primary("🚀 Ejecutar análisis SEO", use_container_width=True):
            self._execute_analysis()
    
    def _execute_analysis(self):
        """Ejecuta el análisis semántico"""
        if not st.session_state.json_data:
            Alert.error("❌ Debes cargar un archivo antes de continuar")
            return
        
        with LoadingSpinner.show("Analizando y generando estructura SEO..."):
            try:
                result = self.embeddings_service.analyze_and_group_titles(
                    data=st.session_state.json_data,
                    max_titles_h2=st.session_state.max_titles_h2,
                    max_titles_h3=st.session_state.max_titles_h3,
                    n_clusters_h2=st.session_state.n_clusters_h2,
                    n_clusters_h3=st.session_state.n_clusters_h3,
                    model=st.session_state.model
                )
                
                st.session_state.analysis_result = result
                Alert.success("✅ Árbol SEO generado exitosamente")
                st.rerun()
                
            except Exception as e:
                Alert.error(f"❌ Error durante el análisis: {str(e)}")
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        st.markdown("---")
        st.markdown("### 📊 Resultados del Análisis")
        
        result = st.session_state.analysis_result
        
        # Mostrar H1 generado
        Card.render(
            title="🏷️ H1 Generado",
            content=f"# {result['title']}",
            icon="🎯"
        )
        
        # Mostrar estructura JSON
        DataDisplay.json(
            result,
            title="Estructura SEO Completa",
            expanded=True
        )
        
        # Opciones de exportación
        col1, col2, col3 = st.columns(3)
        
        with col1:
            self._render_download_button()
        
        with col2:
            self._render_drive_upload_button()
        
        with col3:
            if Button.secondary("Nuevo análisis", icon="🔄"):
                st.session_state.analysis_result = None
                st.rerun()
        
        # Vista previa de la estructura
        self._render_structure_preview()
    
    def _render_download_button(self):
        """Renderiza el botón de descarga"""
        json_bytes = json.dumps(
            st.session_state.analysis_result,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")
        
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name="arbol_seo.json",
            mime="application/json"
        )
    
    def _render_drive_upload_button(self):
        """Renderiza el botón de subida a Drive"""
        if Button.secondary("Subir a Drive", icon="☁️"):
            if "proyecto_id" not in st.session_state:
                Alert.warning("Selecciona un proyecto en la barra lateral")
                return
            
            try:
                # Preparar datos
                json_bytes = json.dumps(
                    st.session_state.analysis_result,
                    ensure_ascii=False,
                    indent=2
                ).encode("utf-8")
                
                # Obtener carpeta
                folder_id = self.drive_service.get_or_create_folder(
                    "arboles seo",
                    st.session_state.proyecto_id
                )
                
                # Subir archivo
                link = self.drive_service.upload_file(
                    "arbol_seo.json",
                    json_bytes,
                    folder_id
                )
                
                if link:
                    Alert.success(f"Archivo subido: [Ver en Drive]({link})")
                else:
                    Alert.error("Error al subir archivo")
                    
            except Exception as e:
                Alert.error(f"Error al subir a Drive: {str(e)}")
    
    def _render_structure_preview(self):
        """Renderiza una vista previa de la estructura SEO"""
        st.markdown("#### 🌲 Vista Previa del Árbol SEO")
        
        result = st.session_state.analysis_result
        
        # Mostrar cada H2 con sus H3s
        for h2_item in result.get("H2", []):
            with st.expander(f"📂 {h2_item['titulo']}", expanded=True):
                h3_list = h2_item.get("H3", [])
                if h3_list:
                    for h3 in h3_list:
                        st.markdown(f"    └── 📄 {h3}")
                else:
                    st.caption("    └── Sin H3s asociados")
        
        # Resumen estadístico
        st.markdown("#### 📈 Resumen Estadístico")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total H2", len(result.get("H2", [])))
        
        with col2:
            total_h3 = sum(len(h2.get("H3", [])) for h2 in result.get("H2", []))
            st.metric("Total H3", total_h3)
        
        with col3:
            avg_h3_per_h2 = total_h3 / len(result.get("H2", [])) if result.get("H2") else 0
            st.metric("Promedio H3 por H2", f"{avg_h3_per_h2:.1f}")
