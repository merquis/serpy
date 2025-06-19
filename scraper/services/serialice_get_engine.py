"""
Servicio de Serialización para JetEngine - Reutilizable
Proporciona funciones de serialización PHP para estructuras de datos complejas
"""
import logging
from typing import List, Dict, Any, Union
import phpserialize

logger = logging.getLogger(__name__)

class SerializeGetEngine:
    """Clase para manejar la serialización de datos para JetEngine de WordPress"""
    
    @staticmethod
    def _escape_quotes_in_serialized(serialized_string: str) -> str:
        """
        Escapa las comillas en una cadena serializada PHP
        Convierte "texto" en ""texto""
        
        Args:
            serialized_string: String serializado PHP
            
        Returns:
            String con comillas escapadas
        """
        return serialized_string.replace('"', '""')
    
    @staticmethod
    def serialize_h2_blocks(h2_sections: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Serializa bloques H2 con contenido para JetEngine usando phpserialize
        
        Args:
            h2_sections: Lista de diccionarios con estructura {"titulo": str, "contenido": str}
            
        Returns:
            Dict con clave "bloques_contenido_h2" y valor serializado en PHP
        """
        flat_structure = {}
        
        try:
            if not h2_sections:
                flat_structure["bloques_contenido_h2"] = ""
                return flat_structure
            
            # Construir estructura para php_serialize
            php_data = {}
            for i, section in enumerate(h2_sections):
                titulo = section.get("titulo", "")
                contenido = section.get("contenido", "")
                
                # Procesar contenido (añadir <p> y salto de línea si es necesario)
                if contenido and not contenido.strip().startswith('<'):
                    contenido = f"<p>{contenido}</p>\n"
                elif contenido and not contenido.endswith('\n'):
                    contenido = f"{contenido}\n"
                
                # Crear estructura con claves item-X como en el CSV
                php_data[f"item-{i}"] = {
                    "titulo_h2": titulo,
                    "parrafo_h2": contenido
                }
            
            # Serializar con phpserialize
            serialized = phpserialize.dumps(php_data)
            
            # Convertir bytes a string si es necesario
            if isinstance(serialized, bytes):
                serialized = serialized.decode('utf-8')
            
            # Escapar comillas
            serialized = SerializeGetEngine._escape_quotes_in_serialized(serialized)
            
            flat_structure["bloques_contenido_h2"] = serialized
            
            logger.info(f"Estructura PHP serializada H2 creada con {len(h2_sections)} secciones usando phpserialize")
            logger.debug(f"Serialización PHP H2 completa: {serialized}")
            
            return flat_structure
            
        except Exception as e:
            logger.error(f"Error creando estructura PHP serializada H2: {e}")
            flat_structure["bloques_contenido_h2"] = ""
            return flat_structure
    
    @staticmethod
    def serialize_custom_fields(data: Dict[str, Any], field_mapping: Dict[str, str] = None) -> Dict[str, str]:
        """
        Serializa campos personalizados genéricos para JetEngine
        
        Args:
            data: Diccionario con los datos a serializar
            field_mapping: Mapeo opcional de claves (clave_original -> clave_destino)
            
        Returns:
            Dict con campos serializados
        """
        try:
            if not data:
                return {}
            
            # Aplicar mapeo de campos si se proporciona
            if field_mapping:
                mapped_data = {}
                for original_key, target_key in field_mapping.items():
                    if original_key in data:
                        mapped_data[target_key] = data[original_key]
                data = mapped_data
            
            # Serializar cada campo que sea una estructura compleja
            serialized_fields = {}
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    # Serializar estructuras complejas
                    serialized = phpserialize.dumps(value)
                    if isinstance(serialized, bytes):
                        serialized = serialized.decode('utf-8')
                    # Escapar comillas
                    serialized = SerializeGetEngine._escape_quotes_in_serialized(serialized)
                    serialized_fields[key] = serialized
                else:
                    # Mantener valores simples como están
                    serialized_fields[key] = str(value) if value is not None else ""
            
            logger.info(f"Campos personalizados serializados: {len(serialized_fields)} campos")
            return serialized_fields
            
        except Exception as e:
            logger.error(f"Error serializando campos personalizados: {e}")
            return {}
    
    @staticmethod
    def serialize_repeater_field(items: List[Dict[str, Any]], field_prefix: str = "item") -> Dict[str, str]:
        """
        Serializa un campo repetidor para JetEngine
        
        Args:
            items: Lista de diccionarios con los elementos del repetidor
            field_prefix: Prefijo para las claves de los elementos (por defecto "item")
            
        Returns:
            Dict con el campo repetidor serializado
        """
        try:
            if not items:
                return {f"{field_prefix}_repeater": ""}
            
            # Construir estructura para el repetidor
            php_data = {}
            for i, item in enumerate(items):
                php_data[f"{field_prefix}-{i}"] = item
            
            # Serializar
            serialized = phpserialize.dumps(php_data)
            if isinstance(serialized, bytes):
                serialized = serialized.decode('utf-8')
            
            # Escapar comillas
            serialized = SerializeGetEngine._escape_quotes_in_serialized(serialized)
            
            logger.info(f"Campo repetidor serializado con {len(items)} elementos")
            return {f"{field_prefix}_repeater": serialized}
            
        except Exception as e:
            logger.error(f"Error serializando campo repetidor: {e}")
            return {f"{field_prefix}_repeater": ""}
    
    @staticmethod
    def serialize_gallery_field(images: List[Dict[str, str]], field_name: str = "gallery") -> Dict[str, str]:
        """
        Serializa un campo de galería de imágenes para JetEngine
        
        Args:
            images: Lista de diccionarios con información de imágenes
            field_name: Nombre del campo de galería
            
        Returns:
            Dict con el campo de galería serializado
        """
        try:
            if not images:
                return {field_name: ""}
            
            # Preparar datos de galería
            gallery_data = {}
            for i, image in enumerate(images):
                gallery_data[f"image-{i}"] = {
                    "url": image.get("image_url", ""),
                    "title": image.get("title", ""),
                    "alt": image.get("alt_text", ""),
                    "caption": image.get("caption", ""),
                    "description": image.get("description", ""),
                    "filename": image.get("filename", "")
                }
            
            # Serializar
            serialized = phpserialize.dumps(gallery_data)
            if isinstance(serialized, bytes):
                serialized = serialized.decode('utf-8')
            
            # Escapar comillas
            serialized = SerializeGetEngine._escape_quotes_in_serialized(serialized)
            
            logger.info(f"Campo de galería serializado con {len(images)} imágenes")
            return {field_name: serialized}
            
        except Exception as e:
            logger.error(f"Error serializando campo de galería: {e}")
            return {field_name: ""}
    
    @staticmethod
    def serialize_meta_fields(meta_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Serializa todos los campos meta de un post para WordPress/JetEngine
        
        Args:
            meta_data: Diccionario con todos los campos meta
            
        Returns:
            Dict con todos los campos meta procesados y serializados según sea necesario
        """
        try:
            processed_meta = {}
            
            for key, value in meta_data.items():
                if isinstance(value, list):
                    if key == "frases_destacadas":
                        # Serializar frases destacadas como repetidor
                        serialized_phrases = SerializeGetEngine.serialize_repeater_field(
                            value, "frase_destacada"
                        )
                        processed_meta.update(serialized_phrases)
                    elif key == "images":
                        # Serializar galería de imágenes
                        gallery_field = SerializeGetEngine.serialize_gallery_field(value, "images_gallery")
                        processed_meta.update(gallery_field)
                    elif key == "servicios":
                        # Serializar lista de servicios
                        services_data = [{"servicio": servicio} for servicio in value]
                        serialized_services = SerializeGetEngine.serialize_repeater_field(
                            services_data, "servicio"
                        )
                        processed_meta.update(serialized_services)
                    else:
                        # Serializar otras listas genéricamente
                        serialized = phpserialize.dumps(value)
                        if isinstance(serialized, bytes):
                            serialized = serialized.decode('utf-8')
                        # Escapar comillas
                        serialized = SerializeGetEngine._escape_quotes_in_serialized(serialized)
                        processed_meta[key] = serialized
                elif isinstance(value, dict):
                    # Serializar diccionarios
                    serialized = phpserialize.dumps(value)
                    if isinstance(serialized, bytes):
                        serialized = serialized.decode('utf-8')
                    # Escapar comillas
                    serialized = SerializeGetEngine._escape_quotes_in_serialized(serialized)
                    processed_meta[key] = serialized
                else:
                    # Mantener valores simples
                    processed_meta[key] = str(value) if value is not None else ""
            
            logger.info(f"Campos meta procesados: {len(processed_meta)} campos")
            return processed_meta
            
        except Exception as e:
            logger.error(f"Error procesando campos meta: {e}")
            return {}
    
    @staticmethod
    def _unescape_quotes_in_serialized(serialized_string: str) -> str:
        """
        Desescapa las comillas en una cadena serializada PHP
        Convierte ""texto"" en "texto"
        
        Args:
            serialized_string: String serializado PHP con comillas escapadas
            
        Returns:
            String con comillas desescapadas
        """
        return serialized_string.replace('""', '"')
    
    @staticmethod
    def deserialize_php_field(serialized_data: str) -> Union[Dict, List, str]:
        """
        Deserializa un campo PHP serializado
        
        Args:
            serialized_data: String con datos serializados en PHP
            
        Returns:
            Datos deserializados o string vacío si hay error
        """
        try:
            if not serialized_data:
                return ""
            
            # Desescapar comillas si están escapadas
            if '""' in serialized_data:
                serialized_data = SerializeGetEngine._unescape_quotes_in_serialized(serialized_data)
                logger.debug("Comillas desescapadas antes de deserializar")
            
            # Intentar deserializar
            if isinstance(serialized_data, str):
                serialized_data = serialized_data.encode('utf-8')
            
            deserialized = phpserialize.loads(serialized_data)
            logger.debug(f"Campo PHP deserializado correctamente")
            return deserialized
            
        except Exception as e:
            logger.error(f"Error deserializando campo PHP: {e}")
            return ""
    
    @staticmethod
    def validate_serialized_data(serialized_data: str) -> bool:
        """
        Valida si un string contiene datos PHP serializados válidos
        
        Args:
            serialized_data: String a validar
            
        Returns:
            True si es válido, False en caso contrario
        """
        try:
            if not serialized_data:
                return False
            
            # Desescapar comillas si están escapadas
            if '""' in serialized_data:
                serialized_data = SerializeGetEngine._unescape_quotes_in_serialized(serialized_data)
            
            # Intentar deserializar para validar
            if isinstance(serialized_data, str):
                serialized_data = serialized_data.encode('utf-8')
            
            phpserialize.loads(serialized_data)
            return True
            
        except Exception:
            return False

# Funciones de conveniencia para uso directo
def serialize_h2_blocks(h2_sections: List[Dict[str, str]]) -> Dict[str, str]:
    """Función de conveniencia para serializar bloques H2"""
    return SerializeGetEngine.serialize_h2_blocks(h2_sections)

def serialize_custom_fields(data: Dict[str, Any], field_mapping: Dict[str, str] = None) -> Dict[str, str]:
    """Función de conveniencia para serializar campos personalizados"""
    return SerializeGetEngine.serialize_custom_fields(data, field_mapping)

def serialize_repeater_field(items: List[Dict[str, Any]], field_prefix: str = "item") -> Dict[str, str]:
    """Función de conveniencia para serializar campos repetidores"""
    return SerializeGetEngine.serialize_repeater_field(items, field_prefix)

def serialize_gallery_field(images: List[Dict[str, str]], field_name: str = "gallery") -> Dict[str, str]:
    """Función de conveniencia para serializar galerías"""
    return SerializeGetEngine.serialize_gallery_field(images, field_name)

def serialize_meta_fields(meta_data: Dict[str, Any]) -> Dict[str, str]:
    """Función de conveniencia para serializar campos meta"""
    return SerializeGetEngine.serialize_meta_fields(meta_data)
