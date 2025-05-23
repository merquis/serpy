import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- Mocks y Fallbacks para importaciones ---
class MockPage:
    def __init__(self, *args, **kwargs): pass
    def render(self): st.info(f"Página {self.__class__.__name__} (Mock o no implementada).")

class MockService:
    def __init__(self, *args, **kwargs): pass

class MockRepository:
    def __init__(self, *args, **kwargs): pass

class MockConfigModule:
    class AppConfig:
        page_title, layout, initial_sidebar_state = "SERPY App", "wide", "expanded"
        app_name, default_project_name = "SERPY", "Default_Project"
        drive_root_folder_id = "YOUR_DRIVE_ROOT_FOLDER_ID_HERE" # CAMBIAR
    class UiConfig:
        icons = {"download": "⬇️", "upload": "⬆️", "clean": "🧹"}
    app = AppConfig()
    ui = UiConfig()

class MockCommonComponent:
    def __init__(self, *args, **kwargs): pass
    def __call__(self, *args, **kwargs):
        if hasattr(self, 'label'): st.write(f"MockComponent: {self.label}")
        return None
    def success(self, msg): st.success(f"MockSuccess: {msg}")
    def error(self, msg): st.error(f"MockError: {msg}")
    def warning(self, msg): st.warning(f"MockWarning: {msg}")
    def info(self, msg): st.info(f"MockInfo: {msg}")
    def primary(self, label, icon=""): return st.button(f"{icon} {label} (MockPrimary)")
    def secondary(self, label, icon=""): return st.button(f"{icon} {label} (MockSecondary)")
    def show(self, label): return st.spinner(f"MockSpinner: {label}")
    def json(self, data, title="", expanded=False): st.json(data, expanded=expanded)
    def render(self, title, description, icon, action_label, action_callback):
        st.warning(f"MockEmptyState: {title} - {description}")
        if st.button(action_label):
            if action_callback: action_callback()

# Define los mocks antes de los try-except de importación de componentes
Alert_mock, Card_mock, Button_mock, LoadingSpinner_mock, DataDisplay_mock, EmptyState_mock = [type(f"Mock{name}", (MockCommonComponent,), {'label': name})() for name in ["Alert", "Card", "Button", "LoadingSpinner", "DataDisplay", "EmptyState"]]

try: from config import config
except ImportError: st.warning("config.py no encontrado, usando MockConfig."); config = MockConfigModule()
try: from services.drive_service import DriveService
except ImportError: st.warning("DriveService no encontrado, usando MockService."); DriveService = type("DriveService", (MockService,), {})

try:
    from ui.components.common import Alert, Card, Button, LoadingSpinner, DataDisplay, EmptyState
except ImportError:
    st.warning("ui.components.common no encontrado, usando Mocks.")
    Alert, Card, Button, LoadingSpinner, DataDisplay, EmptyState = Alert_mock, Card_mock, Button_mock, LoadingSpinner_mock, DataDisplay_mock, EmptyState_mock


PAGES_TO_IMPORT = {
    "GoogleScrapingPage": "ui.pages.google_scraping", "TagScrapingPage": "ui.pages.tag_scraping",
    "ManualScrapingPage": "ui.pages.manual_scraping", "BookingScrapingPage": "ui.pages.booking_scraping",
    "ArticleGeneratorPage": "ui.pages.article_generator", "GPTChatPage": "ui.pages.gpt_chat",
    "EmbeddingsAnalysisPage": "ui.pages.embeddings_analysis",
}
for page_class_name, module_path in PAGES_TO_IMPORT.items():
    try:
        module = __import__(module_path, fromlist=[page_class_name])
        globals()[page_class_name] = getattr(module, page_class_name)
    except ImportError as e:
        st.warning(f"No se pudo importar {page_class_name} desde {module_path}: {e}. Usando MockPage.")
        globals()[page_class_name] = type(page_class_name, (MockPage,), {})
    except AttributeError:
        st.warning(f"Clase {page_class_name} no encontrada en {module_path}. Usando MockPage.")
        globals()[page_class_name] = type(page_class_name, (MockPage,), {})

class SerpyApp:
    def __init__(self):
        self.drive_service = DriveService() if DriveService.__name__ != 'DriveService' else None
        self.setup_page_config()
        self.init_session_state()

    def setup_page_config(self):
        page_title = getattr(config.app, 'page_title', "SERPY App")
        layout = getattr(config.app, 'layout', "wide")
        initial_sidebar_state = getattr(config.app, 'initial_sidebar_state', "expanded")
        app_name = getattr(config.app, 'app_name', "SERPY")

        st.set_page_config(
            page_title=page_title, page_icon="🚀", layout=layout,
            initial_sidebar_state=initial_sidebar_state,
            menu_items={ # --- CORRECCIÓN AQUÍ ---
                'Get Help': 'https://www.example.com/help',  # Reemplaza con URL real o elimina
                'Report a bug': "https://www.example.com/issues", # Reemplaza con URL real o elimina
                'About': f"# {app_name}\nHerramienta SEO y análisis web"
            }
        )
        st.markdown("""<style>.main { padding-top: 1rem; }</style>""", unsafe_allow_html=True)

    def init_session_state(self):
        defaults = {"proyecto_id": None, "proyecto_nombre": getattr(config.app, 'default_project_name', "Default"),
                    "proyectos": {}, "current_page": "scraping_google", "sidebar_project_expanded": False}
        for key, value in defaults.items():
            if key not in st.session_state: st.session_state[key] = value

    def render_sidebar(self):
        with st.sidebar:
            st.markdown(f"# 🚀 {getattr(config.app, 'app_name', 'SERPY')}")
            st.markdown("---")
            # self.render_project_selector()
            st.markdown("---")
            self.render_navigation_menu()
            st.markdown("---")
            st.caption(f"Versión App: 0.1.1")

    def render_project_selector(self): st.write("Selector de Proyecto (Implementar)")

    def render_navigation_menu(self):
        st.markdown("### 🧭 Navegación")
        menu_items_nav = {
            "🔍 Scraping": {"scraping_google": "URLs Google", "scraping_tags": "Etiquetas HTML",
                         "scraping_manual": "URLs manuales", "scraping_booking": "Booking.com"},
            "📝 Contenido": {"article_generator": "Artículos", "gpt_chat": "Chat GPT"},
            "📊 Análisis": {"embeddings_analysis": "Análisis semántico"}
        }
        for section, pages_in_section in menu_items_nav.items():
            st.markdown(f"**{section}**")
            for page_key, page_name in pages_in_section.items():
                if st.button(page_name, key=f"nav_{page_key}", use_container_width=True,
                             type="primary" if st.session_state.current_page == page_key else "secondary"):
                    st.session_state.current_page = page_key
                    st.rerun()

    def render_main_content(self):
        page_map = {
            "scraping_google": GoogleScrapingPage, "scraping_tags": TagScrapingPage,
            "scraping_manual": ManualScrapingPage, "scraping_booking": BookingScrapingPage,
            "article_generator": ArticleGeneratorPage, "gpt_chat": GPTChatPage,
            "embeddings_analysis": EmbeddingsAnalysisPage
        }
        current_page_class = page_map.get(st.session_state.current_page)
        if current_page_class:
            try:
               page_instance = current_page_class()
               page_instance.render()
            except Exception as e:
                st.error(f"Error al renderizar '{st.session_state.current_page}': {e}")
                st.exception(e)
        else: st.error(f"Página '{st.session_state.current_page}' no encontrada.")

    def run(self):
        self.render_sidebar()
        self.render_main_content()

if __name__ == "__main__":
    app = SerpyApp()
    app.run()
