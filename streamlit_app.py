"""
SERPY - Herramienta SEO Profesional
Aplicación principal de Streamlit
"""
import streamlit as st
import sys
import os

# Añadir el directorio /app al path para asegurar importaciones
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Intentar importar config o usar Mock
try:
    from config import config
except ImportError:
    class MockConfig:
        def __init__(self):
            self.app = type('app', (), {})()
            self.app.page_title, self.app.layout, self.app.initial_sidebar_state = "SERPY App", "wide", "expanded"
            self.app.app_name, self.app.default_project_name = "SERPY", "Default"
            self.app.drive_root_folder_id = "YOUR_ROOT_FOLDER_ID" # CAMBIA ESTO
            self.ui = type('ui', (), {})()
            self.ui.icons = {"download": "⬇️", "upload": "⬆️", "clean": "🧹"}
    config = MockConfig()

# Intentar importar DriveService o usar Mock
try:
    from services.drive_service import DriveService
except ImportError:
    DriveService = None

# Placeholder para componentes si no existen
class MockCommon:
    def __call__(self, *args, **kwargs): pass
    def success(self, msg): st.success(msg)
    def error(self, msg): st.error(msg)
    def warning(self, msg): st.warning(msg)
    def info(self, msg): st.info(msg)
    def primary(self, label, icon=""): return st.button(label)
    def secondary(self, label, icon=""): return st.button(label)
    def show(self, label): return st.spinner(label)
    def json(self, data, title="", expanded=False): st.json(data)
    def render(self, title, description, icon, action_label, action_callback): st.warning(title)

try: from ui.components.common import Alert, Card, Button, LoadingSpinner, DataDisplay, EmptyState
except ImportError: Alert, Card, Button, LoadingSpinner, DataDisplay, EmptyState = MockCommon(), MockCommon(), MockCommon(), MockCommon(), MockCommon(), MockCommon()


# Importar páginas
from ui.pages.google_scraping import GoogleScrapingPage
from ui.pages.tag_scraping import TagScrapingPage
