"""
Página de UI para Chat con GPT
"""
import streamlit as st
import json
from typing import Dict, Any, Optional
from ui.components.common import Card, Alert, Button, LoadingSpinner, FileUploader
from services.chat_service import ChatService
from services.drive_service import DriveService
from config import settings

class GPTChatPage:
    """Página para chat libre con GPT"""
    
    def __init__(self):
        self.chat_service = ChatService()
        self.drive_service = DriveService()
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "file_context" not in st.session_state:
            st.session_state.file_context = None
        if "current_provider" not in st.session_state:
            st.session_state.current_provider = "OpenAI"
        if "current_model" not in st.session_state:
            st.session_state.current_model = settings.ai_providers["OpenAI"]["models"][0]
    
    def render(self):
        """Renderiza la página completa"""
        st.title("💬 Chat con IA")
        st.markdown("### 🤖 Conversación sin restricciones con GPT y Claude")
        
        # Selector de modelo en la barra lateral
        self._render_model_selector()
        
        # Sección de carga de archivos
        self._render_file_upload_section()
        
        # Historial de conversación
        self._render_chat_history()
        
        # Input del usuario
        self._render_chat_input()
        
        # Botones de acción
        self._render_action_buttons()
    
    def _render_model_selector(self):
        """Renderiza el selector de modelo en la barra lateral"""
        with st.sidebar:
            st.markdown("### 🤖 Configuración del Modelo")
            
            # Selector de proveedor
            provider = st.selectbox(
                "🏢 Proveedor de IA",
                list(settings.ai_providers.keys()),
                index=list(settings.ai_providers.keys()).index(st.session_state.current_provider),
                key="ai_provider_select"
            )
            
            # Si cambió el proveedor, actualizar el modelo al primero disponible
            if provider != st.session_state.current_provider:
                st.session_state.current_provider = provider
                st.session_state.current_model = settings.ai_providers[provider]["models"][0]
            
            # Selector de modelo basado en el proveedor
            available_models = settings.ai_providers[provider]["models"]
            selected_model = st.selectbox(
                "🤖 Modelo",
                available_models,
                index=available_models.index(st.session_state.current_model) if st.session_state.current_model in available_models else 0,
                key="chat_model_select"
            )
            st.session_state.current_model = selected_model
            
            # Mostrar precios
            price_in, price_out = self.chat_service.get_model_price(selected_model)
            st.markdown(
                f"**💰 Precio por 1M tokens**\n"
                f"- Entrada: ${price_in:.2f}\n"
                f"- Salida: ${price_out:.2f}"
            )
            
            # Parámetros avanzados
            with st.expander("⚙️ Parámetros avanzados", expanded=False):
                st.session_state.temperature = st.slider(
                    "Temperature",
                    0.0, 2.0, 0.7, 0.05,
                    help="Controla la creatividad de las respuestas"
                )
                st.session_state.max_tokens = st.slider(
                    "Max tokens",
                    100, 4000, 1500, 100,
                    help="Máximo de tokens en la respuesta"
                )
    
    def _render_file_upload_section(self):
        """Renderiza la sección de carga de archivos"""
        with st.expander("📁 Analizar archivos", expanded=False):
            st.markdown("Sube archivos para añadirlos como contexto a la conversación")
            
            uploaded_files = st.file_uploader(
                "Tipos soportados: txt, pdf, docx, xlsx, csv, json, zip, imágenes",
                type=["txt", "pdf", "docx", "xlsx", "csv", "json", "zip", "jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="chat_file_uploader"
            )
            
            if uploaded_files:
                with LoadingSpinner.show("Procesando archivos..."):
                    context = self.chat_service.create_file_context(uploaded_files)
                    if context:
                        st.session_state.file_context = context
                        Alert.success(f"✅ {len(uploaded_files)} archivo(s) procesado(s) y añadido(s) al contexto")
                    else:
                        Alert.error("No se pudo procesar ningún archivo")
            
            # Mostrar estado del contexto
            if st.session_state.file_context:
                st.info("📎 Hay archivos en el contexto de la conversación")
                if st.button("🗑️ Limpiar contexto de archivos"):
                    st.session_state.file_context = None
                    st.rerun()
    
    def _render_chat_history(self):
        """Renderiza el historial de chat"""
        st.markdown("### 📝 Historial de conversación")
        
        # Contenedor con altura fija para el chat
        chat_container = st.container(height=400)
        
        with chat_container:
            if not st.session_state.chat_history:
                st.caption("No hay mensajes aún. ¡Empieza la conversación!")
            else:
                for message in st.session_state.chat_history:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
    
    def _render_chat_input(self):
        """Renderiza el input del chat"""
        if prompt := st.chat_input("Escribe tu mensaje aquí..."):
            # Añadir mensaje del usuario al historial
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            # Preparar mensajes para la API
            messages = []
            
            # Añadir contexto de archivos si existe
            if st.session_state.file_context:
                messages.append({
                    "role": "system",
                    "content": st.session_state.file_context
                })
            
            # Añadir historial de chat
            messages.extend(st.session_state.chat_history)
            
            # Generar respuesta
            provider = "Claude" if st.session_state.current_model.startswith("claude") else "GPT"
            with LoadingSpinner.show(f"{provider} está pensando..."):
                try:
                    # Obtener respuesta en streaming
                    response_stream = self.chat_service.generate_response(
                        messages=messages,
                        model=st.session_state.current_model,
                        temperature=st.session_state.get("temperature", 0.7),
                        max_tokens=st.session_state.get("max_tokens", 1500),
                        stream=True
                    )
                    
                    # Mostrar respuesta en streaming
                    with st.chat_message("assistant"):
                        full_response = st.write_stream(response_stream)
                    
                    # Añadir respuesta al historial
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": full_response
                    })
                    
                    # Recargar para actualizar el historial
                    st.rerun()
                    
                except Exception as e:
                    provider = "Claude" if st.session_state.current_model.startswith("claude") else "OpenAI"
                    error_msg = f"❌ Error al contactar con {provider}: {str(e)}"
                    Alert.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
    
    def _render_action_buttons(self):
        """Renderiza los botones de acción"""
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            self._render_download_button()
        
        with col2:
            self._render_drive_upload_button()
        
        with col3:
            self._render_clear_button()
    
    def _render_download_button(self):
        """Renderiza el botón de descarga"""
        if st.session_state.chat_history:
            # Preparar datos para exportación
            export_data = self.chat_service.format_conversation_for_export(
                messages=st.session_state.chat_history,
                model=st.session_state.current_model,
                metadata={
                    "has_file_context": bool(st.session_state.file_context),
                    "temperature": st.session_state.get("temperature", 0.7),
                    "max_tokens": st.session_state.get("max_tokens", 1500)
                }
            )
            
            json_content = json.dumps(export_data, ensure_ascii=False, indent=2)
            
            st.download_button(
                label="⬇️ Descargar JSON",
                data=json_content,
                file_name=f"chat_gpt_{st.session_state.current_model}_{export_data['timestamp'][:10]}.json",
                mime="application/json",
                disabled=False
            )
        else:
            st.button("⬇️ Descargar JSON", disabled=True)
    
    def _render_drive_upload_button(self):
        """Renderiza el botón de subida a Drive"""
        disabled = not st.session_state.chat_history or "proyecto_id" not in st.session_state
        
        if Button.secondary("☁️ Subir a Drive", disabled=disabled, icon="☁️"):
            try:
                # Preparar datos
                export_data = self.chat_service.format_conversation_for_export(
                    messages=st.session_state.chat_history,
                    model=st.session_state.current_model,
                    metadata={
                        "has_file_context": bool(st.session_state.file_context),
                        "temperature": st.session_state.get("temperature", 0.7),
                        "max_tokens": st.session_state.get("max_tokens", 1500)
                    }
                )
                
                json_bytes = json.dumps(export_data, ensure_ascii=False, indent=2).encode("utf-8")
                filename = f"chat_gpt_{st.session_state.current_model}_{export_data['timestamp'][:10]}.json"
                
                # Obtener carpeta
                folder_id = self.drive_service.get_or_create_folder(
                    "chat libre",
                    st.session_state.proyecto_id
                )
                
                # Subir archivo
                link = self.drive_service.upload_file(filename, json_bytes, folder_id)
                
                if link:
                    Alert.success(f"✅ Subido correctamente: [Ver en Drive]({link})")
                else:
                    Alert.error("❌ Error al subir el historial a Drive")
                    
            except Exception as e:
                Alert.error(f"Error al subir a Drive: {str(e)}")
    
    def _render_clear_button(self):
        """Renderiza el botón de limpiar historial"""
        if Button.primary(
            "🧹 Borrar Historial",
            disabled=not st.session_state.chat_history,
            icon="🗑️"
        ):
            st.session_state.chat_history = []
            st.session_state.file_context = None
            Alert.info("Historial borrado")
            st.rerun()
