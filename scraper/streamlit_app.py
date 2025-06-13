"""
SERPY - Herramienta SEO Profesional
Aplicación principal de Streamlit

Este módulo implementa la interfaz principal del scraper SERPY usando Streamlit.
Proporciona una interfaz web para realizar scraping de Google y Booking.com,
generar artículos con IA, y realizar análisis semántico de contenido.

Características principales:
- Scraping de resultados de búsqueda de Google
- Extracción de datos estructurados de páginas web
- Búsqueda y extracción de hoteles de Booking.com
- Generación de artículos con GPT
- Análisis semántico con embeddings
- Integración con Google Drive para almacenamiento
"""
import streamlit as st
from datetime import datetime
from config.settings import settings, normalize_project_name
from ui.components.common import Alert, Card, EmptyState
from services.drive_service import DriveService
from repositories.mongo_repository import MongoRepository

# Importar páginas
from ui.pages.google_buscar import GoogleBuscarPage
from ui.pages.google_extraer_datos import GoogleExtraerDatosPage
from ui.pages.booking_buscar_hoteles import BookingBuscarHotelesPage
from ui.pages.booking_extraer_datos import BookingExtraerDatosPage
from ui.pages.article_generator import ArticleGeneratorPage
from ui.pages.gpt_chat import GPTChatPage
from ui.pages.embeddings_analysis import EmbeddingsAnalysisPage

class SerpyApp:
    """
    Aplicación principal de SERPY.
    
    Gestiona la interfaz de usuario, navegación entre páginas,
    y la integración con Google Drive para el almacenamiento
    de proyectos y resultados.
    """
    
    def __init__(self):
        self.drive_service = DriveService()
        self.setup_page_config()
        self.init_session_state()
    
    def check_project_exists(self, project_name: str) -> bool:
        """
        Verifica si ya existe un proyecto con ese nombre en MongoDB.
        
        Args:
            project_name: Nombre del proyecto a verificar
            
        Returns:
            bool: True si el proyecto existe, False si no existe
        """
        try:
            # Normalizar nombre del proyecto
            normalized_name = normalize_project_name(project_name)
            
            # Conectar a MongoDB
            mongo = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
            
            # Buscar en la colección proyectos por normalized_name
            existing_project = mongo.find_one(
                {"normalized_name": normalized_name},
                collection_name="proyectos"
            )
            
            return existing_project is not None
            
        except Exception as e:
            # En caso de error, asumir que no existe para permitir creación
            st.error(f"Error verificando proyecto: {str(e)}")
            return False
        
    def setup_page_config(self):
        """
        Configura la página de Streamlit.
        
        Establece el título, icono, layout y menú de la aplicación.
        También aplica estilos CSS personalizados para mejorar la UI.
        """
        st.set_page_config(
            page_title=settings.page_title,
            page_icon="🚀",
            layout=settings.layout,
            initial_sidebar_state=settings.initial_sidebar_state,
            menu_items={
                'Get Help': 'https://github.com/serpy/docs',
                'Report a bug': "https://github.com/serpy/issues",
                'About': f"# {settings.app_name}\nHerramienta profesional de SEO y análisis web"
            }
        )
        
        # Aplicar estilos CSS personalizados
        self.apply_custom_styles()
    
    def apply_custom_styles(self):
        """
        Aplica estilos CSS personalizados para mejorar la apariencia.
        
        Incluye estilos para:
        - Métricas con bordes y sombras
        - Botones con efectos hover
        - Expanders con fondo personalizado
        - Sidebar con color de fondo
        """
        st.markdown("""
        <style>
        /* Mejorar aspecto general */
        .main {
            padding-top: 1rem;
        }
        
        /* Estilo para métricas */
        [data-testid="metric-container"] {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
        }
        
        /* Mejorar botones */
        .stButton > button {
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        
        /* Estilo para expanders */
        .streamlit-expanderHeader {
            background-color: #f8f9fa;
            border-radius: 0.5rem;
        }
        
        /* Sidebar mejorado */
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def init_session_state(self):
        """
        Inicializa el estado de la sesión de Streamlit.
        
        Establece valores por defecto para:
        - proyecto_id: ID del proyecto actual en Drive
        - proyecto_nombre: Nombre del proyecto actual
        - proyectos: Diccionario de proyectos disponibles
        - current_page: Página actualmente seleccionada
        - sidebar_project_expanded: Estado del expander de proyectos
        """
        defaults = {
            "proyecto_id": None,
            "proyecto_nombre": settings.default_project_name,
            "proyectos": {},
            "current_page": "scraping_google",
            "sidebar_project_expanded": False,
            "project_input_key": 0
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def render_sidebar(self):
        """
        Renderiza la barra lateral con navegación y configuración.
        
        Incluye:
        - Logo y título de la aplicación
        - Selector de proyectos
        - Menú de navegación principal
        - Información adicional y tips
        """
        with st.sidebar:
            # Logo y título
            st.markdown(f"# 🚀 {settings.app_name}")
            st.markdown("---")
            
            # Selector de proyecto
            self.render_project_selector()
            st.markdown("---")
            
            # Menú de navegación
            self.render_navigation_menu()
            
            # Información adicional
            st.markdown("---")
            self.render_sidebar_footer()
    
    def render_project_selector(self):
        """
        Renderiza el selector de proyectos en la sidebar.
        
        Permite:
        - Cargar proyectos desde Google Drive
        - Seleccionar proyecto activo
        - Crear nuevos proyectos
        """
        with st.expander("📁 Gestión de Proyectos", expanded=st.session_state.sidebar_project_expanded):
            # Cargar proyectos desde Drive
            if st.button("🔄 Actualizar proyectos", use_container_width=True):
                self.load_projects()
                st.session_state.sidebar_project_expanded = True
            
            # Selector de proyecto
            if st.session_state.proyectos:
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    proyecto_actual = st.selectbox(
                        "Proyecto activo:",
                        options=list(st.session_state.proyectos.keys()),
                        index=0 if st.session_state.proyecto_nombre not in st.session_state.proyectos else 
                              list(st.session_state.proyectos.keys()).index(st.session_state.proyecto_nombre)
                    )
                    
                    if proyecto_actual != st.session_state.proyecto_nombre:
                        st.session_state.proyecto_nombre = proyecto_actual
                        st.session_state.proyecto_id = st.session_state.proyectos[proyecto_actual]
                        st.rerun()
                
                with col2:
                    # Añadir estilo para centrar verticalmente el botón
                    st.markdown("""
                        <style>
                        div[data-testid="column"]:last-child {
                            display: flex;
                            align-items: center;
                            padding-top: 1.5rem;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    if st.button("🗑️", help="Eliminar proyecto", use_container_width=True):
                        st.session_state.show_delete_confirmation = True
                
                # Mostrar confirmación de eliminación
                if st.session_state.get("show_delete_confirmation", False):
                    st.warning(f"⚠️ ¿Estás seguro de que quieres eliminar el proyecto '{proyecto_actual}'?")
                    st.caption("Esta acción eliminará todos los datos asociados al proyecto.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Sí, eliminar", type="primary", use_container_width=True):
                            self.delete_project(proyecto_actual)
                            st.session_state.show_delete_confirmation = False
                    with col2:
                        if st.button("❌ Cancelar", use_container_width=True):
                            st.session_state.show_delete_confirmation = False
                            st.rerun()
            
            # Crear nuevo proyecto - dentro de un expander
            with st.expander("➕ Crear nuevo proyecto", expanded=False):
                # Formulario de creación
                with st.form(key=f"create_project_form_{st.session_state.project_input_key}"):
                    # Nombre del proyecto
                    nuevo_nombre = st.text_input(
                        "Nombre del proyecto:", 
                        help="Nombre descriptivo para tu proyecto"
                    )
                    
                    # Mostrar nombre normalizado
                    if nuevo_nombre.strip():
                        normalized = normalize_project_name(nuevo_nombre.strip())
                        st.caption(f"Nombre normalizado: `{normalized}`")
                    
                    # Descripción
                    descripcion = st.text_area(
                        "Descripción:",
                        placeholder="Describe brevemente el proyecto...",
                        help="Opcional: Una breve descripción del proyecto"
                    )
                    
                    # Idioma por defecto
                    idioma = st.selectbox(
                        "Idioma por defecto:",
                        options=["es", "en", "fr", "de"],
                        format_func=lambda x: {
                            "es": "🇪🇸 Español",
                            "en": "🇬🇧 Inglés",
                            "fr": "🇫🇷 Francés",
                            "de": "🇩🇪 Alemán"
                        }[x],
                        help="Idioma principal del proyecto"
                    )
                    
                    # Estado inicial
                    estado = st.radio(
                        "Estado inicial:",
                        options=["active", "development"],
                        format_func=lambda x: "⚡ Activo" if x == "active" else "🔧 En desarrollo",
                        horizontal=True
                    )
                    
                    # Botón de envío
                    submitted = st.form_submit_button(
                        "➕ Crear proyecto",
                        use_container_width=True
                    )
                    
                    if submitted:
                        if not nuevo_nombre.strip():
                            st.error("❌ El nombre del proyecto es obligatorio")
                        elif self.check_project_exists(nuevo_nombre.strip()):
                            st.error("❌ Este nombre ya existe, elige otro")
                        else:
                            self.create_new_project(
                                nombre=nuevo_nombre.strip(),
                                descripcion=descripcion.strip() if descripcion else "",
                                idioma=idioma,
                                estado=estado
                            )
    
    def render_navigation_menu(self):
        """
        Renderiza el menú de navegación principal.
        
        Organiza las páginas en secciones:
        - Scraping: Herramientas de extracción de datos
        - Contenido: Generación y chat con IA
        - Análisis: Herramientas de análisis semántico
        """
        st.markdown("### 🧭 Navegación")
        
        # Definir estructura del menú
        menu_items = {
            "🔍 Scraping": {
                "scraping_google": "Buscar en Google",
                "scraping_tags": "Extraer datos web Google",
                "booking_search": "Buscar hoteles Booking",
                "scraping_booking": "Extraer hoteles Booking"
            },
            "📝 Contenido": {
                "article_generator": "Generador de artículos",
                "gpt_chat": "Chat GPT"
            },
            "📊 Análisis": {
                "embeddings_analysis": "Análisis semántico"
            }
        }
        
        # Renderizar menú
        for section, pages in menu_items.items():
            st.markdown(f"**{section}**")
            for page_key, page_name in pages.items():
                if st.button(
                    page_name, 
                    key=f"nav_{page_key}",
                    use_container_width=True,
                    type="primary" if st.session_state.current_page == page_key else "secondary"
                ):
                    st.session_state.current_page = page_key
                    st.rerun()
    
    def render_sidebar_footer(self):
        """
        Renderiza el pie de la barra lateral.
        
        Muestra tips de uso y versión de la aplicación.
        """
        st.caption("💡 **Tips:**")
        st.caption("• Usa Ctrl+K para búsqueda rápida")
        st.caption("• Los cambios se guardan automáticamente")
        st.caption(f"• Versión: 2.0.0")
    
    def load_projects(self):
        """
        Carga los proyectos desde MongoDB.
        
        Obtiene todos los proyectos de la colección 'proyectos' y los
        almacena en el estado de sesión. Selecciona "TripToIslands"
        por defecto si existe.
        """
        try:
            # Conectar a MongoDB
            mongo = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
            
            # Obtener todos los proyectos
            projects = mongo.find_many(
                filter_dict={},
                collection_name="proyectos",
                sort=[("created_at", -1)]  # Ordenar por fecha de creación descendente
            )
            
            # Convertir a diccionario {nombre: _id}
            proyectos = {}
            for project in projects:
                proyectos[project["name"]] = project["_id"]
            
            st.session_state.proyectos = proyectos
            
            # Seleccionar TripToIslands por defecto si existe
            default_project_name = "TripToIslands"
            if default_project_name in st.session_state.proyectos:
                st.session_state.proyecto_nombre = default_project_name
                st.session_state.proyecto_id = st.session_state.proyectos[default_project_name]
            elif st.session_state.proyectos:  # Si no está TripToIslands pero hay otros, seleccionar el primero
                first_project_name = list(st.session_state.proyectos.keys())[0]
                st.session_state.proyecto_nombre = first_project_name
                st.session_state.proyecto_id = st.session_state.proyectos[first_project_name]
            else:  # No hay proyectos
                st.session_state.proyecto_nombre = None
                st.session_state.proyecto_id = None
                
        except Exception as e:
            Alert.error(f"Error al cargar proyectos: {str(e)}")
    
    def create_new_project(self, nombre: str, descripcion: str = "", idioma: str = "es", estado: str = "active"):
        """
        Crea un nuevo proyecto en MongoDB.
        
        Args:
            nombre: Nombre del nuevo proyecto
            descripcion: Descripción del proyecto
            idioma: Idioma por defecto (es, en, fr, de)
            estado: Estado inicial (active, development)
            
        Crea el proyecto en la colección 'proyectos' y configura el proyecto activo.
        """
        try:
            # 1. Normalizar nombre del proyecto
            normalized_name = normalize_project_name(nombre)
            
            # 2. Verificación final de disponibilidad (doble check)
            if self.check_project_exists(nombre):
                Alert.error("El proyecto ya existe")
                return
            
            # 3. Conectar a MongoDB
            mongo = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
            
            # 4. Crear documento del proyecto
            now = datetime.now().isoformat()
            project_doc = {
                "name": nombre,
                "normalized_name": normalized_name,
                "description": descripcion,
                "default_language": idioma,
                "status": estado,
                "created_at": now,
                "updated_at": now,
                "last_activity": now
            }
            
            # 5. Insertar en la colección proyectos
            project_id = mongo.insert_one(project_doc, collection_name="proyectos")
            
            if project_id:
                # 6. Opcionalmente crear carpeta en Drive (para compatibilidad)
                try:
                    folder_id = self.drive_service.create_folder(nombre, settings.drive_root_folder_id)
                    # Actualizar el documento con el folder_id
                    mongo.update_one(
                        {"_id": project_id},
                        {"drive_folder_id": folder_id},
                        collection_name="proyectos"
                    )
                except Exception as drive_error:
                    # Si falla Drive, continuar sin él
                    st.warning(f"No se pudo crear carpeta en Drive: {drive_error}")
                    folder_id = None
                
                # 7. Configurar proyecto activo
                st.session_state.proyecto_nombre = nombre
                st.session_state.proyecto_id = project_id
                st.session_state.proyectos[nombre] = project_id
                
                # 8. Incrementar el key para limpiar el formulario
                st.session_state.project_input_key += 1
                
                Alert.success(f"✅ Proyecto '{nombre}' creado correctamente")
                st.rerun()
            else:
                Alert.error("Error al crear el proyecto en MongoDB")
                
        except Exception as e:
            Alert.error(f"Error al crear proyecto: {str(e)}")
    
    def delete_project(self, project_name: str):
        """
        Elimina un proyecto y todas sus colecciones asociadas.
        
        Args:
            project_name: Nombre del proyecto a eliminar
        """
        try:
            # Conectar a MongoDB
            mongo = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
            
            # Obtener información del proyecto
            project = mongo.find_one(
                {"name": project_name},
                collection_name="proyectos"
            )
            
            if not project:
                Alert.error(f"No se encontró el proyecto '{project_name}'")
                return
            
            normalized_name = project.get("normalized_name")
            
            # Listar todas las colecciones
            all_collections = mongo.db.list_collection_names()
            
            # Filtrar colecciones del proyecto
            project_collections = [
                col for col in all_collections 
                if col.startswith(f"{normalized_name}_")
            ]
            
            # Guardar información antes de eliminar
            collections_info = f"Eliminando {len(project_collections)} colecciones del proyecto '{project_name}'..."
            
            # Eliminar cada colección del proyecto PRIMERO
            deleted_count = 0
            failed_collections = []
            
            for collection in project_collections:
                try:
                    # Eliminar todos los documentos y la colección
                    mongo.db[collection].drop()
                    deleted_count += 1
                except Exception as e:
                    failed_collections.append(f"{collection}: {str(e)}")
            
            # Ahora eliminar el documento del proyecto de la colección "proyectos"
            try:
                from bson import ObjectId
                # Convertir el _id a ObjectId si es necesario
                if isinstance(project["_id"], str):
                    project_object_id = ObjectId(project["_id"])
                else:
                    project_object_id = project["_id"]
                
                deleted = mongo.delete_one(
                    {"_id": project_object_id},
                    collection_name="proyectos"
                )
                
                if deleted:
                    # Actualizar estado de sesión
                    if st.session_state.proyecto_nombre == project_name:
                        st.session_state.proyecto_nombre = None
                        st.session_state.proyecto_id = None
                    
                    # Eliminar del diccionario de proyectos
                    if project_name in st.session_state.proyectos:
                        del st.session_state.proyectos[project_name]
                    
                    # Mostrar resultado simplificado
                    Alert.success(f"✅ Proyecto '{project_name}' eliminado correctamente")
                    
                    # Limpiar el estado de confirmación de eliminación
                    st.session_state.show_delete_confirmation = False
                    
                    # Recargar proyectos
                    self.load_projects()
                    st.rerun()
                else:
                    Alert.error("No se pudo eliminar el documento del proyecto de la base de datos")
                    
            except Exception as e:
                Alert.error(f"Error al eliminar el proyecto de la colección 'proyectos': {str(e)}")
                
        except Exception as e:
            Alert.error(f"Error general al eliminar proyecto: {str(e)}")
    
    def render_main_content(self):
        """
        Renderiza el contenido principal según la página seleccionada.
        
        Mapea cada página a su clase correspondiente y la renderiza.
        Si no hay proyecto seleccionado (excepto para GPT Chat),
        muestra un mensaje para seleccionar o crear uno.
        """
        # Mapeo de páginas
        pages = {
            "scraping_google": GoogleBuscarPage,
            "scraping_tags": GoogleExtraerDatosPage,
            "booking_search": BookingBuscarHotelesPage,
            "scraping_booking": BookingExtraerDatosPage,
            "article_generator": ArticleGeneratorPage,
            "gpt_chat": GPTChatPage,
            "embeddings_analysis": EmbeddingsAnalysisPage
        }
        
        # Verificar si hay un proyecto seleccionado
        if not st.session_state.proyecto_id and st.session_state.current_page != "gpt_chat":
            EmptyState.render(
                title="No hay proyecto seleccionado",
                description="Por favor, selecciona o crea un proyecto en la barra lateral para continuar",
                icon="📁",
                action_label="Cargar proyectos",
                action_callback=self.load_projects
            )
            return
        
        # Renderizar página seleccionada
        current_page_class = pages.get(st.session_state.current_page)
        
        if current_page_class:
            try:
                # Instanciar y renderizar la página
                page = current_page_class()
                page.render()
            except Exception as e:
                # Si hay un error, mostrar detalles para debugging
                Alert.error(f"Error al cargar la página '{st.session_state.current_page}': {str(e)}")
                st.markdown("### 🚧 Error en la página")
                st.write(f"Error: {str(e)}")
                # Mostrar traceback para debugging
                import traceback
                st.code(traceback.format_exc())
        else:
            Alert.error("Página no encontrada")
    
    def run(self):
        """
        Ejecuta la aplicación principal.
        
        Carga proyectos al inicio si es necesario y renderiza
        la interfaz completa (sidebar + contenido principal).
        """
        # Cargar proyectos al inicio si no están cargados
        if not st.session_state.proyectos:
            self.load_projects()
        
        # Renderizar interfaz
        self.render_sidebar()
        self.render_main_content()

def main():
    """
    Punto de entrada de la aplicación.
    
    Crea una instancia de SerpyApp y la ejecuta.
    """
    app = SerpyApp()
    app.run()

if __name__ == "__main__":
    main()
