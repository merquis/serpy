"""
Página de UI para Scraping Manual de URLs
"""
import streamlit as st
from ui.components.common import Alert

class ManualScrapingPage:
    """Página para scraping manual de URLs"""
    
    def render(self):
        """Renderiza la página"""
        st.title("✋ Scraping Manual de URLs")
        Alert.info("Esta funcionalidad está siendo migrada a la nueva arquitectura...")
        
        # TODO: Implementar la funcionalidad completa
        st.write("Por favor, espera mientras terminamos de migrar esta funcionalidad.") 