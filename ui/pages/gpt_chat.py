"""
Página de UI para Chat con GPT
"""
import streamlit as st
from ui.components.common import Alert

class GPTChatPage:
    """Página para chat libre con GPT"""
    
    def render(self):
        """Renderiza la página"""
        st.title("💬 Chat con GPT")
        Alert.info("Esta funcionalidad está siendo migrada a la nueva arquitectura...")
        
        # TODO: Implementar la funcionalidad completa
        st.write("Por favor, espera mientras terminamos de migrar esta funcionalidad.") 