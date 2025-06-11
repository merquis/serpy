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
            
            # Buscar colección específica de referencia
            reference_collection = f"{normalized_name}_urls_google"
            
            # Listar todas las colecciones
            collections = mongo.db.list_collection_names()
            
            # Verificar si existe la colección de referencia
            return reference_collection in collections
            
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
            
            # Crear nuevo proyecto
            st.markdown("#### Crear nuevo proyecto")
            nuevo_nombre = st.text_input(
                "Nombre del proyecto:", 
                key=f"nuevo_proyecto_input_{st.session_state.project_input_key}",
                help="Presiona Enter para verificar disponibilidad"
            )
            
            # Validación en tiempo real
            button_disabled = True
            if nuevo_nombre.strip():
                normalized = normalize_project_name(nuevo_nombre.strip())
                st.caption(f"Nombre normalizado: `{normalized}`")
                
                # Verificar disponibilidad
                if self.check_project_exists(nuevo_nombre.strip()):
                    st.error("❌ Este nombre ya existe, elige otro")
                    button_disabled = True
                else:
                    st.success("✅ Nombre disponible")
                    button_disabled = False
            else:
                st.caption("Introduce un nombre para el proyecto")
            
            # Botón deshabilitado si hay problemas
            if st.button("➕ Crear proyecto", use_container_width=True, disabled=button_disabled):
                self.create_new_project(nuevo_nombre.strip())
    
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
        Carga los proyectos desde Google Drive.
        
        Lista las carpetas en la carpeta raíz configurada y las
        almacena en el estado de sesión. Selecciona "TripToIslands"
        por defecto si existe.
        """
        try:
            proyectos = self.drive_service.list_folders(settings.drive_root_folder_id)
            st.session_state.proyectos = proyectos
            
            # Seleccionar TripToIslands por defecto si existe
            default_project_name = "TripToIslands"
            if default_project_name in st.session_state.proyectos:
                st.session_state.proyecto_nombre = default_project_name
                st.session_state.proyecto_id = st.session_state.proyectos[default_project_name]
            elif st.session_state.proyectos: # Si no está TripToIslands pero hay otros, seleccionar el primero
                first_project_name = list(st.session_state.proyectos.keys())[0]
                st.session_state.proyecto_nombre = first_project_name
                st.session_state.proyecto_id = st.session_state.proyectos[first_project_name]
            else: # No hay proyectos
                st.session_state.proyecto_nombre = settings.default_project_name
                st.session_state.proyecto_id = None
        except Exception as e:
            Alert.error(f"Error al cargar proyectos: {str(e)}")
    
    def create_new_project(self, nombre: str):
        """
        Crea un nuevo proyecto en Google Drive y MongoDB.
        
        Args:
            nombre: Nombre del nuevo proyecto
            
        Crea una carpeta en Drive, inicializa las colecciones en MongoDB y configura el proyecto activo.
        """
        try:
            # 1. Normalizar nombre del proyecto
            normalized_name = normalize_project_name(nombre)
            
            # 2. Verificación final de disponibilidad (doble check)
            if self.check_project_exists(nombre):
                Alert.error("El proyecto ya existe")
                return
            
            # 3. Crear directorio en Google Drive (con nombre original)
            folder_id = self.drive_service.create_folder(nombre, settings.drive_root_folder_id)
            
            if folder_id:
                # 4. Inicializar colecciones en MongoDB
                mongo = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
                
                # Crear colección de referencia con un documento inicial
                reference_collection = f"{normalized_name}_urls_google"
                initial_doc = {
                    "project_name": normalized_name,
                    "original_name": nombre,
                    "created_at": datetime.now().isoformat(),
                    "status": "initialized",
                    "description": f"Proyecto creado: {nombre}"
                }
                
                # Insertar documento inicial para crear la colección
                mongo.insert_one(initial_doc, collection_name=reference_collection)
                
                # 5. Configurar proyecto activo
                st.session_state.proyecto_nombre = normalized_name
                st.session_state.proyecto_id = folder_id
                st.session_state.proyectos[normalized_name] = folder_id
                
                # 6. Incrementar el key para limpiar el campo de entrada
                st.session_state.project_input_key += 1
                
                Alert.success(f"Proyecto '{normalized_name}' creado correctamente en Drive y MongoDB")
                st.rerun()
            else:
                Alert.error("Error al crear la carpeta en Google Drive")
        except Exception as e:
            Alert.error(f"Error al crear proyecto: {str(e)}")
    
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
