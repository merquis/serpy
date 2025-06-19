"""
Página de UI para herramientas de serialización PHP
"""
import streamlit as st
import json
from typing import Dict, Any, List
from ui.components.common import Card, Alert, Button, DataDisplay
from services.serialice_get_engine import SerializeGetEngine
import logging

logger = logging.getLogger(__name__)

class SerializacionToolsPage:
    """Página para herramientas de serialización y deserialización PHP"""
    
    def __init__(self):
        self._init_session_state()
    
    def _init_session_state(self):
        """Inicializa el estado de la sesión"""
        defaults = {
            "serialization_mode": "Serializar",
            "input_data_type": "Bloques H2",
            "input_text": "",
            "serialized_output": "",
            "deserialized_output": "",
            "custom_field_mapping": "{}",
            "repeater_prefix": "item",
            "gallery_field_name": "gallery"
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def render(self):
        """Renderiza la página principal"""
        st.title("🔧 Herramientas de Serialización PHP")
        st.markdown("### 🔄 Serializa y deserializa datos para JetEngine de WordPress")
        
        # Selector de modo
        st.session_state.serialization_mode = st.radio(
            "Selecciona el modo:",
            ["Serializar", "Deserializar"],
            horizontal=True,
            index=0 if st.session_state.serialization_mode == "Serializar" else 1
        )
        
        if st.session_state.serialization_mode == "Serializar":
            self._render_serialization_section()
        else:
            self._render_deserialization_section()
    
    def _render_serialization_section(self):
        """Renderiza la sección de serialización"""
        st.markdown("## 📦 Serializar Datos")
        
        # Selector de tipo de datos
        st.session_state.input_data_type = st.selectbox(
            "Tipo de datos a serializar:",
            ["Bloques H2", "Campos Personalizados", "Campo Repetidor", "Galería de Imágenes", "Meta Fields Completos"],
            index=["Bloques H2", "Campos Personalizados", "Campo Repetidor", "Galería de Imágenes", "Meta Fields Completos"].index(st.session_state.input_data_type)
        )
        
        # Renderizar formulario específico según el tipo
        if st.session_state.input_data_type == "Bloques H2":
            self._render_h2_blocks_form()
        elif st.session_state.input_data_type == "Campos Personalizados":
            self._render_custom_fields_form()
        elif st.session_state.input_data_type == "Campo Repetidor":
            self._render_repeater_field_form()
        elif st.session_state.input_data_type == "Galería de Imágenes":
            self._render_gallery_form()
        elif st.session_state.input_data_type == "Meta Fields Completos":
            self._render_meta_fields_form()
    
    def _render_h2_blocks_form(self):
        """Formulario para serializar bloques H2"""
        st.markdown("### 📝 Bloques H2 con Contenido")
        
        # Ejemplo predefinido
        ejemplo_h2 = '''[
    {
        "titulo": "Ubicación privilegiada",
        "contenido": "Este hotel se encuentra en el corazón de la ciudad, cerca de los principales puntos de interés turístico."
    },
    {
        "titulo": "Servicios destacados",
        "contenido": "<h3>Spa y bienestar</h3>Disfruta de nuestro spa completo con tratamientos relajantes. <h3>Restaurante gourmet</h3>Cocina internacional de alta calidad."
    },
    {
        "titulo": "Habitaciones",
        "contenido": "Todas nuestras habitaciones están equipadas con las mejores comodidades para garantizar una estancia perfecta."
    }
]'''
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.session_state.input_text = st.text_area(
                "Introduce los datos JSON de bloques H2:",
                value=st.session_state.input_text or ejemplo_h2,
                height=300,
                help="Formato: Lista de objetos con 'titulo' y 'contenido'"
            )
        with col2:
            if st.button("📋 Usar Ejemplo", key="h2_ejemplo"):
                st.session_state.input_text = ejemplo_h2
                st.rerun()
        
        if st.button("🔄 Serializar Bloques H2", type="primary"):
            self._serialize_h2_blocks()
    
    def _render_custom_fields_form(self):
        """Formulario para serializar campos personalizados"""
        st.markdown("### ⚙️ Campos Personalizados")
        
        ejemplo_custom = '''{
    "servicios": ["WiFi gratuito", "Piscina", "Gimnasio", "Spa"],
    "valoraciones": {
        "limpieza": 9.2,
        "ubicacion": 8.8,
        "personal": 9.5
    },
    "precio_noche": "150.00",
    "nombre": "Hotel Ejemplo"
}'''
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.session_state.input_text = st.text_area(
                "Introduce los datos JSON:",
                value=st.session_state.input_text or ejemplo_custom,
                height=200,
                help="Formato: Objeto JSON con los campos a serializar"
            )
        with col2:
            if st.button("📋 Usar Ejemplo", key="custom_ejemplo"):
                st.session_state.input_text = ejemplo_custom
                st.rerun()
        
        # Mapeo de campos opcional
        st.session_state.custom_field_mapping = st.text_area(
            "Mapeo de campos (opcional):",
            value=st.session_state.custom_field_mapping,
            height=100,
            help='Formato: {"campo_original": "campo_destino"}'
        )
        
        if st.button("🔄 Serializar Campos Personalizados", type="primary"):
            self._serialize_custom_fields()
    
    def _render_repeater_field_form(self):
        """Formulario para serializar campo repetidor"""
        st.markdown("### 🔁 Campo Repetidor")
        
        ejemplo_repeater = '''[
    {"nombre": "WiFi gratuito", "descripcion": "Internet de alta velocidad"},
    {"nombre": "Piscina", "descripcion": "Piscina climatizada disponible 24h"},
    {"nombre": "Gimnasio", "descripcion": "Equipamiento moderno y completo"}
]'''
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.session_state.input_text = st.text_area(
                "Introduce los datos JSON del repetidor:",
                value=st.session_state.input_text or ejemplo_repeater,
                height=200,
                help="Formato: Lista de objetos con los elementos del repetidor"
            )
        with col2:
            if st.button("📋 Usar Ejemplo", key="repeater_ejemplo"):
                st.session_state.input_text = ejemplo_repeater
                st.rerun()
        
        st.session_state.repeater_prefix = st.text_input(
            "Prefijo para los elementos:",
            value=st.session_state.repeater_prefix,
            help="Prefijo que se usará para las claves (ej: 'item', 'servicio')"
        )
        
        if st.button("🔄 Serializar Campo Repetidor", type="primary"):
            self._serialize_repeater_field()
    
    def _render_gallery_form(self):
        """Formulario para serializar galería"""
        st.markdown("### 🖼️ Galería de Imágenes")
        
        ejemplo_gallery = '''[
    {
        "image_url": "https://example.com/hotel_001.jpg",
        "title": "hotel_ejemplo_001",
        "alt_text": "Vista exterior del hotel",
        "caption": "Fachada principal",
        "description": "Vista de la fachada principal del hotel",
        "filename": "hotel_ejemplo_001.jpg"
    },
    {
        "image_url": "https://example.com/hotel_002.jpg",
        "title": "hotel_ejemplo_002",
        "alt_text": "Habitación deluxe",
        "caption": "Suite deluxe",
        "description": "Interior de la suite deluxe con vista al mar",
        "filename": "hotel_ejemplo_002.jpg"
    }
]'''
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.session_state.input_text = st.text_area(
                "Introduce los datos JSON de la galería:",
                value=st.session_state.input_text or ejemplo_gallery,
                height=300,
                help="Formato: Lista de objetos con información de imágenes"
            )
        with col2:
            if st.button("📋 Usar Ejemplo", key="gallery_ejemplo"):
                st.session_state.input_text = ejemplo_gallery
                st.rerun()
        
        st.session_state.gallery_field_name = st.text_input(
            "Nombre del campo de galería:",
            value=st.session_state.gallery_field_name,
            help="Nombre que tendrá el campo de galería serializado"
        )
        
        if st.button("🔄 Serializar Galería", type="primary"):
            self._serialize_gallery()
    
    def _render_meta_fields_form(self):
        """Formulario para serializar meta fields completos"""
        st.markdown("### 📋 Meta Fields Completos")
        
        ejemplo_meta = '''{
    "nombre_alojamiento": "Hotel Ejemplo Premium",
    "precio_noche": "180.50",
    "valoracion_global": "9.1",
    "frases_destacadas": [
        {"frase_destacada": "Ubicación excepcional"},
        {"frase_destacada": "Servicio de primera clase"},
        {"frase_destacada": "Vistas espectaculares"}
    ],
    "servicios": ["WiFi", "Piscina", "Spa", "Restaurante"],
    "images": [
        {
            "image_url": "https://example.com/img1.jpg",
            "title": "Imagen 1",
            "alt_text": "Alt text 1"
        }
    ],
    "valoraciones_detalladas": {
        "limpieza": 9.2,
        "ubicacion": 8.9,
        "personal": 9.5
    }
}'''
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.session_state.input_text = st.text_area(
                "Introduce los datos JSON completos:",
                value=st.session_state.input_text or ejemplo_meta,
                height=400,
                help="Formato: Objeto JSON con todos los campos meta"
            )
        with col2:
            if st.button("📋 Usar Ejemplo", key="meta_ejemplo"):
                st.session_state.input_text = ejemplo_meta
                st.rerun()
        
        if st.button("🔄 Serializar Meta Fields", type="primary"):
            self._serialize_meta_fields()
    
    def _render_deserialization_section(self):
        """Renderiza la sección de deserialización"""
        st.markdown("## 📤 Deserializar Datos PHP")
        
        # Ejemplo de datos PHP serializados
        ejemplo_serializado = 'a:3:{s:6:"item-0";a:2:{s:9:"titulo_h2";s:23:"Ubicación privilegiada";s:10:"parrafo_h2";s:116:"<p>Este hotel se encuentra en el corazón de la ciudad, cerca de los principales puntos de interés turístico.</p>\n";}s:6:"item-1";a:2:{s:9:"titulo_h2";s:20:"Servicios destacados";s:10:"parrafo_h2";s:152:"<h3>Spa y bienestar</h3>Disfruta de nuestro spa completo con tratamientos relajantes. <h3>Restaurante gourmet</h3>Cocina internacional de alta calidad.\n";}s:6:"item-2";a:2:{s:9:"titulo_h2";s:12:"Habitaciones";s:10:"parrafo_h2";s:119:"<p>Todas nuestras habitaciones están equipadas con las mejores comodidades para garantizar una estancia perfecta.</p>\n";}}'
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.session_state.input_text = st.text_area(
                "Introduce los datos PHP serializados:",
                value=st.session_state.input_text or "",
                height=300,
                help="Pega aquí los datos serializados en formato PHP, JSON con campos serializados, o formato campo:valor"
            )
        with col2:
            if st.button("📋 Usar Ejemplo", key="deserialize_ejemplo"):
                st.session_state.input_text = ejemplo_serializado
                st.rerun()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Deserializar", type="primary"):
                self._deserialize_data_auto()
        with col2:
            if st.button("✅ Validar Datos", type="secondary"):
                self._validate_serialized_data_auto()
    
    def _serialize_h2_blocks(self):
        """Serializa bloques H2"""
        try:
            data = json.loads(st.session_state.input_text)
            if not isinstance(data, list):
                Alert.error("Los datos deben ser una lista de objetos")
                return
            
            result = SerializeGetEngine.serialize_h2_blocks(data)
            st.session_state.serialized_output = result
            
            Alert.success(f"✅ Bloques H2 serializados correctamente")
            self._display_serialization_result(result)
            
        except json.JSONDecodeError as e:
            Alert.error(f"Error en el formato JSON: {str(e)}")
        except Exception as e:
            Alert.error(f"Error al serializar: {str(e)}")
    
    def _serialize_custom_fields(self):
        """Serializa campos personalizados"""
        try:
            data = json.loads(st.session_state.input_text)
            
            # Procesar mapeo de campos si existe
            field_mapping = None
            if st.session_state.custom_field_mapping.strip():
                field_mapping = json.loads(st.session_state.custom_field_mapping)
            
            result = SerializeGetEngine.serialize_custom_fields(data, field_mapping)
            st.session_state.serialized_output = result
            
            Alert.success(f"✅ Campos personalizados serializados correctamente")
            self._display_serialization_result(result)
            
        except json.JSONDecodeError as e:
            Alert.error(f"Error en el formato JSON: {str(e)}")
        except Exception as e:
            Alert.error(f"Error al serializar: {str(e)}")
    
    def _serialize_repeater_field(self):
        """Serializa campo repetidor"""
        try:
            data = json.loads(st.session_state.input_text)
            if not isinstance(data, list):
                Alert.error("Los datos deben ser una lista de objetos")
                return
            
            result = SerializeGetEngine.serialize_repeater_field(data, st.session_state.repeater_prefix)
            st.session_state.serialized_output = result
            
            Alert.success(f"✅ Campo repetidor serializado correctamente")
            self._display_serialization_result(result)
            
        except json.JSONDecodeError as e:
            Alert.error(f"Error en el formato JSON: {str(e)}")
        except Exception as e:
            Alert.error(f"Error al serializar: {str(e)}")
    
    def _serialize_gallery(self):
        """Serializa galería de imágenes"""
        try:
            data = json.loads(st.session_state.input_text)
            if not isinstance(data, list):
                Alert.error("Los datos deben ser una lista de objetos de imágenes")
                return
            
            result = SerializeGetEngine.serialize_gallery_field(data, st.session_state.gallery_field_name)
            st.session_state.serialized_output = result
            
            Alert.success(f"✅ Galería serializada correctamente")
            self._display_serialization_result(result)
            
        except json.JSONDecodeError as e:
            Alert.error(f"Error en el formato JSON: {str(e)}")
        except Exception as e:
            Alert.error(f"Error al serializar: {str(e)}")
    
    def _serialize_meta_fields(self):
        """Serializa meta fields completos"""
        try:
            data = json.loads(st.session_state.input_text)
            if not isinstance(data, dict):
                Alert.error("Los datos deben ser un objeto JSON")
                return
            
            result = SerializeGetEngine.serialize_meta_fields(data)
            st.session_state.serialized_output = result
            
            Alert.success(f"✅ Meta fields serializados correctamente ({len(result)} campos procesados)")
            self._display_serialization_result(result)
            
        except json.JSONDecodeError as e:
            Alert.error(f"Error en el formato JSON: {str(e)}")
        except Exception as e:
            Alert.error(f"Error al serializar: {str(e)}")
    
    def _deserialize_data(self, input_type: str):
        """Deserializa datos PHP"""
        try:
            if not st.session_state.input_text.strip():
                Alert.error("Introduce datos serializados para deserializar")
                return
            
            input_text = st.session_state.input_text.strip()
            
            # Detección automática del formato
            if input_type == "JSON con campos serializados":
                # Primero intentar como JSON
                try:
                    json_data = json.loads(input_text)
                    deserialized_fields = {}
                    
                    for field_name, field_value in json_data.items():
                        if isinstance(field_value, str) and SerializeGetEngine.validate_serialized_data(field_value):
                            # Es un campo serializado, deserializarlo
                            deserialized_value = SerializeGetEngine.deserialize_php_field(field_value)
                            deserialized_fields[field_name] = {
                                "original_serialized": field_value,
                                "deserialized": deserialized_value
                            }
                        else:
                            # No es un campo serializado, mantenerlo como está
                            deserialized_fields[field_name] = {
                                "original_value": field_value,
                                "deserialized": field_value
                            }
                    
                    st.session_state.deserialized_output = deserialized_fields
                    Alert.success("✅ JSON procesado correctamente")
                    self._display_json_deserialization_result(deserialized_fields)
                    return
                    
                except json.JSONDecodeError as e:
                    # Si falla como JSON, intentar extraer el valor serializado
                    try:
                        import re
                        
                        # Patrón 1: "campo":"valor_serializado" (formato completo)
                        pattern1 = r'"([^"]+)"\s*:\s*"(a:\d+:\{.*?\}\})"'
                        match1 = re.search(pattern1, input_text, re.DOTALL)
                        
                        if match1:
                            field_name = match1.group(1)
                            serialized_value = match1.group(2)
                            
                            Alert.info(f"🔄 Detectado formato campo:valor completo. Extrayendo '{field_name}'...")
                            
                            if SerializeGetEngine.validate_serialized_data(serialized_value):
                                result = SerializeGetEngine.deserialize_php_field(serialized_value)
                                if result:
                                    Alert.success(f"✅ Campo '{field_name}' deserializado correctamente")
                                    st.session_state.deserialized_output = result
                                    self._display_deserialization_result(result)
                                    return
                                else:
                                    Alert.error(f"❌ La deserialización devolvió un resultado vacío")
                                    return
                            else:
                                Alert.error(f"❌ El valor del campo '{field_name}' no es PHP serializado válido")
                                return
                        
                        # Patrón 2: "campo":"valor_serializado" (formato incompleto - sin comillas finales)
                        pattern2 = r'"([^"]+)"\s*:\s*"(a:\d+:\{.*)'
                        match2 = re.search(pattern2, input_text, re.DOTALL)
                        
                        if match2:
                            field_name = match2.group(1)
                            serialized_value = match2.group(2)
                            
                            # Limpiar el valor serializado (quitar comillas finales si las hay)
                            serialized_value = serialized_value.rstrip('"')
                            
                            Alert.info(f"🔄 Detectado formato campo:valor incompleto. Extrayendo '{field_name}'...")
                            
                            # Intentar corregir valores serializados incompletos
                            if not SerializeGetEngine.validate_serialized_data(serialized_value):
                                Alert.warning("⚠️ Valor serializado parece incompleto, intentando corregir...")
                                
                                # Verificar si es un array serializado que necesita cierre
                                if serialized_value.startswith('a:') and not serialized_value.endswith('}}'):
                                    # Contar llaves abiertas vs cerradas
                                    open_braces = serialized_value.count('{')
                                    close_braces = serialized_value.count('}')
                                    missing_braces = open_braces - close_braces
                                    
                                    if missing_braces > 0:
                                        corrected_value = serialized_value + ('}' * missing_braces)
                                        Alert.info(f"🔧 Añadiendo {missing_braces} llave(s) de cierre...")
                                        
                                        if SerializeGetEngine.validate_serialized_data(corrected_value):
                                            Alert.success("✅ Valor corregido automáticamente")
                                            result = SerializeGetEngine.deserialize_php_field(corrected_value)
                                            if result:
                                                Alert.success(f"✅ Campo '{field_name}' deserializado correctamente")
                                                self._display_deserialization_result(result)
                                                return
                                        else:
                                            Alert.error("❌ No se pudo corregir automáticamente el valor")
                                            return
                                
                                Alert.error(f"❌ El valor del campo '{field_name}' no es PHP serializado válido")
                                return
                            else:
                                result = SerializeGetEngine.deserialize_php_field(serialized_value)
                                if result:
                                    Alert.success(f"✅ Campo '{field_name}' deserializado correctamente")
                                    self._display_deserialization_result(result)
                                    return
                        
                        # Patrón 3: JSON incompleto {"campo":"valor"
                        pattern3 = r'\{"([^"]+)"\s*:\s*"([^"]*a:\d+:\{[^}]*\}[^"]*)"'
                        match3 = re.search(pattern3, input_text, re.DOTALL)
                        
                        if match3:
                            field_name = match3.group(1)
                            serialized_value = match3.group(2)
                            
                            Alert.info(f"🔄 Detectado JSON incompleto. Extrayendo campo '{field_name}'...")
                            
                            if SerializeGetEngine.validate_serialized_data(serialized_value):
                                result = SerializeGetEngine.deserialize_php_field(serialized_value)
                                if result:
                                    Alert.success(f"✅ Campo '{field_name}' deserializado correctamente")
                                    self._display_deserialization_result(result)
                                    return
                            else:
                                Alert.error(f"❌ El valor del campo '{field_name}' no es PHP serializado válido")
                                return
                                
                    except Exception as extract_error:
                        pass
                    
                    # Si falla como JSON, verificar si es un valor serializado directo
                    if SerializeGetEngine.validate_serialized_data(input_text):
                        Alert.info("🔄 Detectado valor serializado directo, procesando...")
                        # Procesar como valor serializado directo
                        result = SerializeGetEngine.deserialize_php_field(input_text)
                        if result:
                            Alert.success("✅ Valor serializado deserializado correctamente")
                            self._display_deserialization_result(result)
                        else:
                            Alert.error("❌ No se pudo deserializar el valor")
                        return
                    else:
                        # Mostrar error más específico
                        Alert.error(f"❌ Error en JSON: {str(e)}")
                        Alert.info("💡 Sugerencias:")
                        st.info("• Verifica que el JSON esté completo (con todas las llaves y comillas cerradas)")
                        st.info("• O pega solo el valor serializado (sin las comillas del campo)")
                        st.info("• O selecciona 'Datos PHP serializados directos' si tienes solo el valor")
                        return
            else:
                # Deserialización directa de datos PHP serializados
                result = SerializeGetEngine.deserialize_php_field(input_text)
                st.session_state.deserialized_output = result
                
                if result:
                    Alert.success("✅ Datos deserializados correctamente")
                    self._display_deserialization_result(result)
                else:
                    Alert.error("❌ No se pudieron deserializar los datos")
                
        except Exception as e:
            Alert.error(f"Error al deserializar: {str(e)}")
    
    def _validate_serialized_data(self, input_type: str):
        """Valida datos serializados"""
        try:
            if not st.session_state.input_text.strip():
                Alert.error("Introduce datos para validar")
                return
            
            input_text = st.session_state.input_text.strip()
            
            if input_type == "JSON con campos serializados":
                # Primero intentar como JSON
                try:
                    json_data = json.loads(input_text)
                    serialized_fields = []
                    valid_fields = []
                    invalid_fields = []
                    
                    for field_name, field_value in json_data.items():
                        if isinstance(field_value, str):
                            is_valid = SerializeGetEngine.validate_serialized_data(field_value)
                            if is_valid:
                                serialized_fields.append(field_name)
                                valid_fields.append(field_name)
                            else:
                                # Verificar si parece ser un campo serializado pero está mal formado
                                if field_value.startswith('a:') or field_value.startswith('s:'):
                                    invalid_fields.append(field_name)
                    
                    if serialized_fields:
                        Alert.success(f"✅ JSON válido con {len(valid_fields)} campos serializados correctos: {', '.join(valid_fields)}")
                        if invalid_fields:
                            Alert.warning(f"⚠️ Campos con serialización inválida: {', '.join(invalid_fields)}")
                    else:
                        Alert.info("ℹ️ JSON válido pero no contiene campos PHP serializados")
                        
                except json.JSONDecodeError:
                    # Si falla como JSON, verificar si es un valor serializado directo
                    if SerializeGetEngine.validate_serialized_data(input_text):
                        Alert.success("✅ Valor PHP serializado válido (detectado automáticamente)")
                    else:
                        Alert.error("❌ El texto no es un JSON válido ni un valor PHP serializado válido")
            else:
                # Validación directa de datos PHP serializados
                is_valid = SerializeGetEngine.validate_serialized_data(input_text)
                
                if is_valid:
                    Alert.success("✅ Los datos están correctamente serializados en formato PHP")
                else:
                    Alert.error("❌ Los datos no están en formato PHP serializado válido")
                    
        except Exception as e:
            Alert.error(f"Error al validar: {str(e)}")
    
    def _display_serialization_result(self, result: Dict[str, Any]):
        """Muestra el resultado de la serialización"""
        st.markdown("### 📤 Resultado de la Serialización")
        
        for field_name, serialized_value in result.items():
            with st.expander(f"📋 Campo: {field_name}", expanded=True):
                st.text_area(
                    "Valor serializado:",
                    value=serialized_value,
                    height=150,
                    key=f"result_{field_name}",
                    help="Copia este valor para usar en WordPress/JetEngine"
                )
    
    def _display_deserialization_result(self, result: Any):
        """Muestra el resultado de la deserialización"""
        st.markdown("### 📥 Resultado de la Deserialización")
        
        if result is None:
            st.error("❌ El resultado de la deserialización es None")
            return
        
        if isinstance(result, dict) and len(result) == 0:
            st.warning("⚠️ El resultado es un diccionario vacío")
            return
        
        if isinstance(result, list) and len(result) == 0:
            st.warning("⚠️ El resultado es una lista vacía")
            return
        
        # Convertir bytes a strings si es necesario
        result = self._convert_bytes_to_str(result)
        
        # Mostrar como JSON formateado
        try:
            json_result = json.dumps(result, ensure_ascii=False, indent=2)
            st.text_area(
                "Datos deserializados:",
                value=json_result,
                height=400,
                help="Datos originales recuperados del formato PHP serializado"
            )
            
            # Si es un array de bloques H2, mostrar resumen
            if isinstance(result, dict) and all(k.startswith('item-') for k in result.keys()):
                st.markdown("#### 📋 Resumen de bloques H2:")
                for key, value in result.items():
                    if isinstance(value, dict) and 'titulo_h2' in value:
                        st.write(f"• **{value.get('titulo_h2', 'Sin título')}**")
                        
        except Exception as e:
            st.error(f"Error al convertir a JSON: {e}")
            st.write("Datos deserializados (raw):")
            st.write(result)
    
    def _display_json_deserialization_result(self, deserialized_fields: Dict[str, Any]):
        """Muestra el resultado de la deserialización de JSON con campos serializados"""
        st.markdown("### 📥 Resultado del Procesamiento JSON")
        
        for field_name, field_data in deserialized_fields.items():
            if "original_serialized" in field_data:
                # Campo que estaba serializado
                with st.expander(f"🔓 Campo deserializado: {field_name}", expanded=True):
                    st.markdown("**Datos deserializados:**")
                    try:
                        json_result = json.dumps(field_data["deserialized"], ensure_ascii=False, indent=2)
                        st.text_area(
                            "Contenido deserializado:",
                            value=json_result,
                            height=200,
                            key=f"deserialized_{field_name}",
                            help="Datos originales recuperados del campo serializado"
                        )
                    except Exception:
                        st.write(field_data["deserialized"])
            else:
                # Campo que no estaba serializado
                with st.expander(f"📄 Campo normal: {field_name}", expanded=False):
                    st.write("**Valor original (no serializado):**")
                    st.write(field_data["original_value"])
        
        # Mostrar resumen
        serialized_count = sum(1 for field_data in deserialized_fields.values() if "original_serialized" in field_data)
        normal_count = len(deserialized_fields) - serialized_count
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total campos", len(deserialized_fields))
        col2.metric("Campos deserializados", serialized_count)
        col3.metric("Campos normales", normal_count)
    
    def _convert_bytes_to_str(self, data: Any) -> Any:
        """Convierte recursivamente bytes a strings en estructuras de datos"""
        if isinstance(data, bytes):
            return data.decode('utf-8', errors='replace')
        elif isinstance(data, dict):
            return {self._convert_bytes_to_str(k): self._convert_bytes_to_str(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._convert_bytes_to_str(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self._convert_bytes_to_str(item) for item in data)
        else:
            return data
    
    def _deserialize_data_auto(self):
        """Deserializa datos PHP con detección automática del formato"""
        try:
            if not st.session_state.input_text.strip():
                Alert.error("Introduce datos para deserializar")
                return
            
            input_text = st.session_state.input_text.strip()
            
            # Intentar detectar el formato automáticamente
            import re
            
            # 1. Verificar si es un valor PHP serializado directo
            if SerializeGetEngine.validate_serialized_data(input_text):
                Alert.info("🔄 Detectado formato PHP serializado directo")
                result = SerializeGetEngine.deserialize_php_field(input_text)
                if result:
                    # Convertir bytes a strings
                    result = self._convert_bytes_to_str(result)
                    Alert.success("✅ Datos deserializados correctamente")
                    self._display_deserialization_result(result)
                else:
                    Alert.error("❌ No se pudieron deserializar los datos")
                return
            
            # 2. Verificar si es formato "campo":"valor"
            pattern_campo_valor = r'"([^"]+)"\s*:\s*"(a:\d+:\{[^"]*)"'
            match = re.search(pattern_campo_valor, input_text, re.DOTALL)
            if match:
                field_name = match.group(1)
                serialized_value = match.group(2)
                
                # Limpiar el valor
                serialized_value = serialized_value.rstrip('"')
                
                Alert.info(f"🔄 Detectado formato campo:valor. Extrayendo '{field_name}'...")
                
                # Verificar si necesita corrección
                if not SerializeGetEngine.validate_serialized_data(serialized_value):
                    if serialized_value.startswith('a:') and not serialized_value.endswith('}}'):
                        open_braces = serialized_value.count('{')
                        close_braces = serialized_value.count('}')
                        missing_braces = open_braces - close_braces
                        
                        if missing_braces > 0:
                            serialized_value = serialized_value + ('}' * missing_braces)
                            Alert.info(f"🔧 Corregido automáticamente: añadidas {missing_braces} llave(s)")
                
                if SerializeGetEngine.validate_serialized_data(serialized_value):
                    result = SerializeGetEngine.deserialize_php_field(serialized_value)
                    if result:
                        # Convertir bytes a strings
                        result = self._convert_bytes_to_str(result)
                        Alert.success(f"✅ Campo '{field_name}' deserializado correctamente")
                        self._display_deserialization_result(result)
                    else:
                        Alert.error("❌ No se pudo deserializar el valor")
                else:
                    Alert.error("❌ El valor no es PHP serializado válido")
                return
            
            # 3. Intentar como JSON
            try:
                json_data = json.loads(input_text)
                Alert.info("🔄 Detectado formato JSON")
                
                # Buscar campos serializados
                found_serialized = False
                for field_name, field_value in json_data.items():
                    if isinstance(field_value, str) and SerializeGetEngine.validate_serialized_data(field_value):
                        found_serialized = True
                        Alert.info(f"📍 Encontrado campo serializado: '{field_name}'")
                        result = SerializeGetEngine.deserialize_php_field(field_value)
                        if result:
                            # Convertir bytes a strings
                            result = self._convert_bytes_to_str(result)
                            Alert.success(f"✅ Campo '{field_name}' deserializado")
                            self._display_deserialization_result(result)
                            break
                
                if not found_serialized:
                    Alert.warning("⚠️ JSON válido pero sin campos PHP serializados")
                return
                
            except json.JSONDecodeError:
                pass
            
            # Si no se detectó ningún formato
            Alert.error("❌ No se pudo detectar el formato de los datos")
            Alert.info("💡 Formatos soportados:")
            st.info("• Datos PHP serializados directos: a:3:{s:6:\"item-0\";...}")
            st.info("• Formato campo:valor: \"bloques_contenido_h2\":\"a:3:{...}\"")
            st.info("• JSON con campos serializados: {\"campo\": \"a:3:{...}\", ...}")
            
        except Exception as e:
            Alert.error(f"Error al deserializar: {str(e)}")
            logger.error(f"Error en deserialización: {e}", exc_info=True)
    
    def _validate_serialized_data_auto(self):
        """Valida datos serializados con detección automática"""
        try:
            if not st.session_state.input_text.strip():
                Alert.error("Introduce datos para validar")
                return
            
            input_text = st.session_state.input_text.strip()
            
            # Validación directa
            if SerializeGetEngine.validate_serialized_data(input_text):
                Alert.success("✅ Datos PHP serializados válidos")
                return
            
            # Buscar en formato campo:valor
            import re
            pattern = r'"([^"]+)"\s*:\s*"(a:\d+:\{[^"]*)"'
            match = re.search(pattern, input_text, re.DOTALL)
            if match:
                field_name = match.group(1)
                serialized_value = match.group(2).rstrip('"')
                
                if SerializeGetEngine.validate_serialized_data(serialized_value):
                    Alert.success(f"✅ Campo '{field_name}' contiene datos PHP serializados válidos")
                else:
                    Alert.warning(f"⚠️ Campo '{field_name}' parece contener datos serializados pero no son válidos")
                return
            
            # Intentar como JSON
            try:
                json_data = json.loads(input_text)
                found_any = False
                for field_name, field_value in json_data.items():
                    if isinstance(field_value, str) and SerializeGetEngine.validate_serialized_data(field_value):
                        Alert.success(f"✅ Campo '{field_name}' contiene datos PHP serializados válidos")
                        found_any = True
                
                if not found_any:
                    Alert.info("ℹ️ JSON válido pero sin campos PHP serializados")
                return
                
            except json.JSONDecodeError:
                pass
            
            Alert.error("❌ No se encontraron datos PHP serializados válidos")
            
        except Exception as e:
            Alert.error(f"Error al validar: {str(e)}")
