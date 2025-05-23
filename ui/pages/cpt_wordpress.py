"""
Página de UI para CPT WordPress
"""
import streamlit as st
from ui.components.common import Alert

class CPTWordPressPage:
    """Página para gestión de Custom Post Types de WordPress"""
    
    def render(self):
        """Renderiza la página"""
        st.title("📝 CPT WordPress")
        Alert.info("Esta funcionalidad está siendo migrada a la nueva arquitectura...")
        
        # TODO: Implementar la funcionalidad completa
        st.write("Por favor, espera mientras terminamos de migrar esta funcionalidad.") 