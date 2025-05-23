"""
SERPY - Herramienta SEO Profesional
Aplicación principal de Streamlit
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# --- BLOQUE CORREGIDO ---
# Definimos la clase Mock PRIMERO
class MockCommon:
    def __call__(self, *args, **kwargs): pass
    def success(self, msg): st.success(msg)
    def error(self, msg): st.error(msg)
    def warning(self, msg): st.warning(msg)
    def info(self, msg): st.info(msg)
    def primary(self, label, icon=""): return st.button(label)
    def secondary(self, label, icon=""): return st.button(label)
    def show(self, label): return st.spinner(label)
    def json(self, data, *args, **kwargs): st.json(data)
    def render(self, title, description, icon, action_label, action_callback):
        st.warning(title)
        st.write(description)
        if st.button(action_label): action_callback()

# Intentamos importar, y si falla, usamos Mocks
try:
    from ui.components.common import Alert, Card, Button, LoadingSpinner, DataDisplay, EmptyState
except ImportError:
    st.warning("Componentes comunes no encontrados, usando Mocks para app.")
    Alert, Card, Button, LoadingSpinner, DataDisplay, EmptyState = MockCommon(), MockCommon(), MockCommon(), MockCommon(), MockCommon(), MockCommon()

try: from config import config
except ImportError:
    class MockConfig:
        def __init__(self):
            self.app = type('app', (), {})()
            self.app.page_title, self.app.layout, self.app.initial_sidebar_state = "SERPY App", "wide", "expanded"
            self.app.app_name, self.app.default_project_name = "SERPY", "Default"
            self.app.drive_root_folder_id = "YOUR_ROOT_FOLDER_ID"
            self.ui = type('ui', (), {})()
            self.ui.icons = {"download": "⬇️", "upload": "⬆️", "clean": "🧹"}
    config = MockConfig()

try: from services.drive_service import DriveService
except ImportError: DriveService = None
# --- FIN BLOQUE CORREGIDO ---


# Placeholder para páginas si no existen
class MockPage:
    def render(self): st.info(f"Página {self.__class__.__name__} (Mock)")

try: from ui.pages.google_scraping import GoogleScrapingPage
except ImportError: GoogleScrapingPage = type("GoogleScrapingPage", (MockPage,), {})
try: from ui.pages.tag_scraping import TagScrapingPage
except ImportError: TagScrapingPage = type("TagScrapingPage", (MockPage,), {})
try: from ui.pages.manual_scraping import ManualScrapingPage
except ImportError: ManualScrapingPage = type("ManualScrapingPage", (MockPage,), {})
try: from ui.pages.booking_scraping import BookingScrapingPage
except ImportError: BookingScrapingPage = type("BookingScrapingPage", (MockPage,), {})
try: from ui.pages.article_generator import ArticleGeneratorPage
except ImportError: ArticleGeneratorPage = type("ArticleGeneratorPage", (MockPage,), {})
try: from ui.pages.gpt_chat import GPTChatPage
except ImportError: GPTChatPage = type("GPTChatPage", (MockPage,), {})
try: from ui.pages.embeddings_analysis import EmbeddingsAnalysisPage
except ImportError: EmbeddingsAnalysisPage = type("EmbeddingsAnalysisPage", (MockPage,), {})


class SerpyApp:
    def __init__(self):
        self.drive_service = DriveService() if DriveService else None
        self.setup_page_config()
        self.init_session_state()

    def setup_page_config(self):
        st.set_page_config(
            page_title=config.app.page_title, page_icon="🚀", layout=config.app.layout,
            initial_sidebar_state=config.app.initial_sidebar_state,
            menu_items={ 'Get Help': '#', 'Report a bug': "#", 'About': f"# {config.app.app_name}"}
        )
        st.markdown("""<style>.main { padding-top: 1rem; }</style>""", unsafe_allow_html=True)

    def init_session_state(self):
        defaults = {"proyecto_id": None, "proyecto_nombre": config.app.default_project_name, "proyectos": {},
                    "current_page": "scraping_google", "sidebar_project_expanded": False}
        for key, value in defaults.items():
            if key not in st.session_state: st.session_state[key] = value

    def render_sidebar(self):
        with st.sidebar:
            st.markdown(f"# 🚀 {config.app.app_name}")
            st.markdown("---")
            # self.render_project_selector() # Comentado por ahora
            st.markdown("---")
            self.render_navigation_menu()
            st.markdown("---")

    def render_navigation_menu(self):
        st.markdown("### 🧭 Navegación")
        menu_items = {
            "🔍 Scraping": {"scraping_google": "URLs Google", "scraping_tags": "Etiquetas HTML",
                         "scraping_manual": "URLs manuales", "scraping_booking": "Booking.com"},
            "📝 Contenido": {"article_generator": "Artículos", "gpt_chat": "Chat GPT"},
            "📊 Análisis": {"embeddings_analysis": "Análisis semántico"}
        }
        for section, pages in menu_items.items():
            st.markdown(f"**{section}**")
            for page_key, page_name in pages.items():
                if st.button(page_name, key=f"nav_{page_key}", use_container_width=True,
                             type="primary" if st.session_state.current_page == page_key else "secondary"):
                    st.session_state.current_page = page_key
                    st.rerun()

    def render_main_content(self):
        pages = {
            "scraping_google": GoogleScrapingPage, "scraping_tags": TagScrapingPage,
            "scraping_manual": ManualScrapingPage, "scraping_booking": BookingScrapingPage,
            "article_generator": ArticleGeneratorPage, "gpt_chat": GPTChatPage,
            "embeddings_analysis": EmbeddingsAnalysisPage
        }
        current_page_class = pages.get(st.session_state.current_page)
        if current_page_class:
            try:
               page = current_page_class()
               page.render()
            except Exception as e:
                st.error(f"Error al renderizar '{st.session_state.current_page}': {e}")
                st.exception(e)
        else: st.error("Página no encontrada")

    def run(self):
        self.render_sidebar()
        self.render_main_content()

if __name__ == "__main__":
    app = SerpyApp()
    app.run()
