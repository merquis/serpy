"""
Página de UI para Generador de Artículos SEO
"""
import streamlit as st
import json
from typing import Dict, Any, Optional
from ui.components.common import Card, Alert, Button, LoadingSpinner, DataDisplay, SelectBox
from services.article_generator_service import ArticleGeneratorService
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository
from config import settings

class ArticleGeneratorPage:
    """Página para generar esquemas y artículos SEO con IA"""
    
    def __init__(self):
        self.article_service = ArticleGeneratorService()
        self.drive_service = DriveService()
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
        if "json_source" not in st.session_state:
            st.session_state.json_source = None
        if "ai_response" not in st.session_state:
            st.session_state.ai_response = None
        if "pre_keyword" not in st.session_state:
            st.session_state.pre_keyword = ""
    
    def render(self):
        """Renderiza la página completa"""
        st.title("📚 Generador de Artículos SEO")
        st.markdown("### 🤖 Genera esquemas y contenidos optimizados para SEO con IA")
        
        # Sección de carga de datos de competencia
        self._render_data_source_section()
        
        # Sección de parámetros principales
        self._render_main_parameters()
        
        # Sección de ajustes avanzados
        self._render_advanced_settings()
        
        # Sección de opciones de generación
        self._render_generation_options()
        
        # Botón de ejecución y estimación de coste
        self._render_execution_section()
        
        # Mostrar resultados si existen
        if st.session_state.ai_response:
            self._render_results_section()
    
    def _render_data_source_section(self):
        """Renderiza la sección de carga de datos de competencia"""
        st.markdown("#### 📊 Datos de Competencia (Opcional)")
        
        source = st.radio(
            "Fuente de datos JSON:",
            ["Ninguno", "Ordenador", "Drive", "MongoDB"],
            horizontal=True
        )
        
        if source == "Ordenador":
            self._handle_file_upload()
        elif source == "Drive":
            self._handle_drive_source()
        elif source == "MongoDB":
            self._handle_mongodb_source()
    
    def _handle_file_upload(self):
        """Maneja la carga de archivo desde el ordenador"""
        uploaded_file = st.file_uploader("Sube un archivo JSON", type=["json"])
        
        if uploaded_file:
            st.session_state.json_source = uploaded_file.read()
            self._preload_keyword(st.session_state.json_source)
            Alert.success(f"Archivo {uploaded_file.name} cargado correctamente")
            st.rerun()
    
    def _handle_drive_source(self):
        """Maneja la carga desde Google Drive"""
        if "proyecto_id" not in st.session_state:
            Alert.info("Selecciona un proyecto en la barra lateral")
            return
        
        try:
            folder_id = self.drive_service.get_or_create_folder(
                "scraper etiquetas google",
                st.session_state.proyecto_id
            )
            
            files = self.drive_service.list_json_files_in_folder(folder_id)
            
            if files:
                selected_file = st.selectbox("Archivo en Drive:", list(files.keys()))
                
                if Button.primary("Cargar desde Drive", icon="📥"):
                    content = self.drive_service.get_file_content(files[selected_file])
                    st.session_state.json_source = content
                    self._preload_keyword(content)
                    Alert.success(f"Archivo {selected_file} cargado desde Drive")
                    st.rerun()
            else:
                Alert.info("No hay archivos JSON en esa carpeta")
                
        except Exception as e:
            Alert.error(f"Error al acceder a Drive: {str(e)}")
    
    def _handle_mongodb_source(self):
        """Maneja la carga desde MongoDB"""
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
        collection_name = get_collection_name(proyecto_activo, "extraer_datos_web_google")
        
        try:
            # Obtener documentos de la colección del proyecto
            documents = self.get_mongo_repo().find_many(
                {},
                collection_name=collection_name,
                limit=100,
                sort=[("_id", -1)]  # Más recientes primero
            )
            
            if documents:
                # Crear opciones para el selector
                options = {}
                for doc in documents:
                    # Buscar información relevante para mostrar
                    busqueda = doc.get("busqueda", "")
                    if not busqueda:
                        # Si no hay campo busqueda, buscar en otros campos
                        busqueda = doc.get("keyword", doc.get("query", "Sin búsqueda"))
                    
                    label = f"{busqueda} - ID: {str(doc.get('_id', ''))[-12:]}"
                    options[label] = doc
                
                selected_key = st.selectbox("Documento:", list(options.keys()))
                
                st.info(f"📊 Cargando desde colección: **{collection_name}** (proyecto: {proyecto_activo})")
                
                if Button.primary("Cargar desde MongoDB", icon="📥"):
                    selected_doc = options[selected_key]
                    content = json.dumps(selected_doc, default=str).encode()
                    st.session_state.json_source = content
                    self._preload_keyword(content)
                    Alert.success(f"Documento cargado desde {collection_name}")
                    st.rerun()
            else:
                st.warning(f"No se encontraron documentos en la colección '{collection_name}'")
                st.info(f"📊 Buscando en colección: **{collection_name}** (proyecto: {proyecto_activo})")
                
        except Exception as e:
            Alert.error(f"Error al acceder a MongoDB: {str(e)}")
    
    def _render_main_parameters(self):
        """Renderiza los parámetros principales"""
        st.markdown("---")
        st.markdown("#### ⚙️ Parámetros Principales")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            keyword = st.text_input(
                "Keyword principal",
                value=st.session_state.pre_keyword,
                help="La palabra clave principal para la que quieres posicionar"
            )
            st.session_state.keyword = keyword
        
        with col2:
            language = st.selectbox(
                "Idioma",
                ["Español", "Inglés", "Francés", "Alemán"],
                index=0
            )
            st.session_state.language = language
        
        with col3:
            content_type = st.selectbox(
                "Tipo de contenido",
                ["Informativo", "Transaccional", "Ficha de producto"],
                index=0
            )
            st.session_state.content_type = content_type
        
        with col4:
            models = settings.gpt_models
            model = st.selectbox(
                "Modelo GPT",
                models,
                index=0
            )
            st.session_state.model = model
    
    def _render_advanced_settings(self):
        """Renderiza los ajustes avanzados"""
        with st.expander("⚙️ Ajustes avanzados", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.temperature = st.slider(
                    "Temperature",
                    0.0, 2.0, 0.9, 0.05,
                    help="Controla la creatividad (mayor = más creativo)"
                )
                st.session_state.top_p = st.slider(
                    "Top-p",
                    0.0, 1.0, 1.0, 0.05,
                    help="Controla la diversidad del vocabulario"
                )
            
            with col2:
                st.session_state.frequency_penalty = st.slider(
                    "Frequency penalty",
                    0.0, 2.0, 0.0, 0.1,
                    help="Reduce la repetición de palabras"
                )
                st.session_state.presence_penalty = st.slider(
                    "Presence penalty",
                    0.0, 2.0, 0.0, 0.1,
                    help="Aumenta la probabilidad de hablar sobre nuevos temas"
                )
    
    def _render_generation_options(self):
        """Renderiza las opciones de generación"""
        st.markdown("#### 📝 Opciones de Generación")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.session_state.generate_schema = st.checkbox(
                "📑 Esquema",
                value=True,
                help="Genera la estructura H1/H2/H3"
            )
        
        with col2:
            st.session_state.generate_text = st.checkbox(
                "✍️ Textos",
                value=False,
                help="Genera contenido completo para cada sección"
            )
        
        with col3:
            st.session_state.generate_slug = st.checkbox(
                "🔗 Slug H1",
                value=True,
                help="Genera URL amigable del H1"
            )
    
    def _render_execution_section(self):
        """Renderiza la sección de ejecución"""
        # Estimación de coste
        est_input = len(st.session_state.json_source or b"") // 4
        est_output = 3000 if st.session_state.get("generate_text", False) else 800
        
        cost_in, cost_out = self.article_service.estimate_cost(
            st.session_state.get("model", "gpt-4o-mini"),
            est_input,
            est_output
        )
        
        st.markdown(
            f"💰 **Coste estimado:** Entrada: ${cost_in:.3f} / "
            f"Salida: ${cost_out:.3f} / "
            f"**Total: ${cost_in + cost_out:.3f}**"
        )
        
        # Botón de ejecución
        if Button.primary("Generar Esquema/Artículo", icon="🚀", use_container_width=True):
            self._execute_generation()
    
    def _execute_generation(self):
        """Ejecuta la generación del esquema/artículo"""
        keyword = st.session_state.get("keyword", "")
        
        if not keyword:
            Alert.warning("Debe introducirse una keyword")
            return
        
        with LoadingSpinner.show("Generando con IA..."):
            try:
                result = self.article_service.generate_article_schema(
                    keyword=keyword,
                    language=st.session_state.get("language", "Español"),
                    content_type=st.session_state.get("content_type", "Informativo"),
                    model=st.session_state.get("model", "gpt-4o-mini"),
                    generate_text=st.session_state.get("generate_text", False),
                    generate_slug=st.session_state.get("generate_slug", True),
                    competition_data=st.session_state.json_source,
                    temperature=st.session_state.get("temperature", 0.9),
                    top_p=st.session_state.get("top_p", 1.0),
                    frequency_penalty=st.session_state.get("frequency_penalty", 0.0),
                    presence_penalty=st.session_state.get("presence_penalty", 0.0)
                )
                
                st.session_state.ai_response = result
                
                # Guardar automáticamente en MongoDB
                self._auto_save_to_mongodb(result)
                
                Alert.success("¡Esquema generado exitosamente!")
                st.rerun()
                
            except Exception as e:
                Alert.error(f"Error al generar: {str(e)}")
    
    def _render_results_section(self):
        """Renderiza la sección de resultados"""
        st.markdown("---")
        st.markdown("### 📄 Resultado Generado")
        
        # Mostrar JSON
        DataDisplay.json(
            st.session_state.ai_response,
            title="Esquema JSON",
            expanded=True
        )
        
        # Opciones de exportación
        col1, col2, col3 = st.columns(3)
        
        with col1:
            self._render_download_button()
        
        with col2:
            self._render_drive_upload_button()
        
        with col3:
            if Button.secondary("Nueva generación", icon="🔄"):
                st.session_state.ai_response = None
                st.rerun()
        
        # Vista previa del contenido
        self._render_content_preview()
    
    def _render_download_button(self):
        """Renderiza el botón de descarga"""
        json_bytes = json.dumps(
            st.session_state.ai_response,
            ensure_ascii=False,
            indent=2
        ).encode("utf-8")
        
        filename = f"{st.session_state.ai_response.get('slug', 'esquema_seo')}.json"
        
        st.download_button(
            label="⬇️ Descargar JSON",
            data=json_bytes,
            file_name=filename,
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
                    st.session_state.ai_response,
                    ensure_ascii=False,
                    indent=2
                ).encode("utf-8")
                
                filename = f"{st.session_state.ai_response.get('slug', 'esquema_seo')}.json"
                
                # Obtener carpeta
                folder_id = self.drive_service.get_or_create_folder(
                    "posts automaticos",
                    st.session_state.proyecto_id
                )
                
                # Subir archivo
                link = self.drive_service.upload_file(
                    filename,
                    json_bytes,
                    folder_id
                )
                
                if link:
                    Alert.success(f"Archivo subido: [Ver en Drive]({link})")
                else:
                    Alert.error("Error al subir archivo")
                    
            except Exception as e:
                Alert.error(f"Error al subir a Drive: {str(e)}")
    
    def _render_content_preview(self):
        """Renderiza una vista previa del contenido generado"""
        data = st.session_state.ai_response
        
        st.markdown("#### 👁️ Vista Previa del Contenido")
        
        # Título principal
        title = data.get("title", "")
        if title:
            st.markdown(f"# {title}")
        
        # Slug
        slug = data.get("slug", "")
        if slug:
            st.caption(f"🔗 URL: /{slug}")
        
        # Contenido del H1
        h1_data = data.get("H1", {})
        # Manejar cuando H1 es un string o un diccionario
        if isinstance(h1_data, str):
            # Si H1 es solo un string, mostrarlo
            if h1_data:
                st.write(h1_data)
        elif isinstance(h1_data, dict) and h1_data.get("contenido"):
            # Si H1 es un diccionario con contenido
            st.write(h1_data["contenido"])
        
        # H2s y H3s
        h2_list = data.get("H2", [])
        for h2 in h2_list:
            if h2.get("titulo"):
                st.markdown(f"## {h2['titulo']}")
                
                if h2.get("contenido"):
                    st.write(h2["contenido"])
                
                # H3s dentro del H2
                h3_list = h2.get("H3", [])
                for h3 in h3_list:
                    if h3.get("titulo"):
                        st.markdown(f"### {h3['titulo']}")
                        
                        if h3.get("contenido"):
                            st.write(h3["contenido"])
        
        # Total de palabras
        total_words = data.get("total_palabras")
        if total_words:
            st.info(f"📊 Total de palabras: {total_words}")
    
    def _auto_save_to_mongodb(self, result: Dict[str, Any]):
        """Guarda automáticamente el artículo en MongoDB"""
        # Verificar que hay un proyecto activo
        if not st.session_state.get("proyecto_nombre"):
            st.warning("⚠️ No se pudo guardar en MongoDB: No hay proyecto activo")
            return
        
        try:
            # Obtener el nombre del proyecto activo y normalizarlo
            proyecto_activo = st.session_state.proyecto_nombre
            
            # Importar la función de normalización y aplicarla
            from config.settings import normalize_project_name
            proyecto_normalizado = normalize_project_name(proyecto_activo)
            
            # Usar sufijo centralizado desde settings
            from config.settings import get_collection_name
            collection_name = get_collection_name(proyecto_activo, "generador_articulos")
            
            # Agregar metadatos del proyecto
            import copy
            from datetime import datetime
            
            article_with_metadata = copy.deepcopy(result)
            timestamp = datetime.now().isoformat()
            article_with_metadata["_guardado_automatico"] = timestamp
            article_with_metadata["_proyecto_activo"] = proyecto_activo
            article_with_metadata["_proyecto_normalizado"] = proyecto_normalizado
            
            # Guardar en MongoDB
            mongo_id = self.get_mongo_repo().insert_one(
                article_with_metadata,
                collection_name=collection_name
            )
            
            st.success(f"✅ Artículo guardado automáticamente en MongoDB (colección: {collection_name}) con ID: `{mongo_id}`")
            
        except Exception as e:
            st.error(f"❌ Error al guardar automáticamente en MongoDB: {str(e)}")
    
    def _preload_keyword(self, json_bytes: bytes):
        """Pre-carga la keyword desde el JSON"""
        keyword = self.article_service.extract_keyword_from_json(json_bytes)
        if keyword:
            st.session_state.pre_keyword = keyword
