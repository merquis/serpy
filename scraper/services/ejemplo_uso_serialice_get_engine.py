"""
Ejemplo de uso del servicio SerializeGetEngine
Demuestra cómo usar las funciones de serialización desde diferentes archivos
"""
from services.serialice_get_engine import SerializeGetEngine, serialize_h2_blocks
import logging

logger = logging.getLogger(__name__)

def ejemplo_serializar_h2_blocks():
    """Ejemplo de cómo serializar bloques H2 para JetEngine"""
    
    # Datos de ejemplo de secciones H2
    h2_sections = [
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
    ]
    
    # Método 1: Usando la clase directamente
    resultado_clase = SerializeGetEngine.serialize_h2_blocks(h2_sections)
    logger.info(f"Resultado usando clase: {resultado_clase}")
    
    # Método 2: Usando la función de conveniencia
    resultado_funcion = serialize_h2_blocks(h2_sections)
    logger.info(f"Resultado usando función: {resultado_funcion}")
    
    return resultado_clase

def ejemplo_serializar_campos_personalizados():
    """Ejemplo de cómo serializar campos personalizados genéricos"""
    
    # Datos de ejemplo
    datos_hotel = {
        "servicios": ["WiFi gratuito", "Piscina", "Gimnasio", "Spa"],
        "valoraciones": {
            "limpieza": 9.2,
            "ubicacion": 8.8,
            "personal": 9.5
        },
        "precio_noche": "150.00",
        "nombre": "Hotel Ejemplo"
    }
    
    # Mapeo de campos (opcional)
    mapeo_campos = {
        "nombre": "nombre_alojamiento",
        "precio_noche": "precio_por_noche"
    }
    
    # Serializar campos personalizados
    resultado = SerializeGetEngine.serialize_custom_fields(datos_hotel, mapeo_campos)
    logger.info(f"Campos personalizados serializados: {resultado}")
    
    return resultado

def ejemplo_serializar_repetidor():
    """Ejemplo de cómo serializar un campo repetidor"""
    
    # Datos de ejemplo para un repetidor de servicios
    servicios = [
        {"nombre": "WiFi gratuito", "descripcion": "Internet de alta velocidad"},
        {"nombre": "Piscina", "descripcion": "Piscina climatizada disponible 24h"},
        {"nombre": "Gimnasio", "descripcion": "Equipamiento moderno y completo"}
    ]
    
    # Serializar como campo repetidor
    resultado = SerializeGetEngine.serialize_repeater_field(servicios, "servicio")
    logger.info(f"Campo repetidor serializado: {resultado}")
    
    return resultado

def ejemplo_serializar_galeria():
    """Ejemplo de cómo serializar una galería de imágenes"""
    
    # Datos de ejemplo de imágenes
    imagenes = [
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
    ]
    
    # Serializar galería
    resultado = SerializeGetEngine.serialize_gallery_field(imagenes, "galeria_hotel")
    logger.info(f"Galería serializada: {resultado}")
    
    return resultado

def ejemplo_serializar_meta_completo():
    """Ejemplo de cómo serializar todos los campos meta de un post"""
    
    # Datos meta completos de ejemplo
    meta_data = {
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
    }
    
    # Serializar todos los campos meta
    resultado = SerializeGetEngine.serialize_meta_fields(meta_data)
    logger.info(f"Meta fields serializados: {len(resultado)} campos procesados")
    
    return resultado

def ejemplo_deserializar():
    """Ejemplo de cómo deserializar datos PHP"""
    
    # Primero serializamos algunos datos
    datos_test = {"titulo": "Test", "contenido": "Contenido de prueba"}
    serializado = SerializeGetEngine.serialize_custom_fields(datos_test)
    
    # Luego los deserializamos
    for campo, valor_serializado in serializado.items():
        if SerializeGetEngine.validate_serialized_data(valor_serializado):
            deserializado = SerializeGetEngine.deserialize_php_field(valor_serializado)
            logger.info(f"Campo '{campo}' deserializado: {deserializado}")
        else:
            logger.info(f"Campo '{campo}' no contiene datos serializados válidos: {valor_serializado}")

def ejemplo_uso_desde_otro_servicio():
    """Ejemplo de cómo usar el servicio desde otro archivo/servicio"""
    
    logger.info("=== Ejemplos de uso de SerializeGetEngine ===")
    
    # Ejemplo 1: Serializar bloques H2
    logger.info("\n1. Serializando bloques H2:")
    ejemplo_serializar_h2_blocks()
    
    # Ejemplo 2: Serializar campos personalizados
    logger.info("\n2. Serializando campos personalizados:")
    ejemplo_serializar_campos_personalizados()
    
    # Ejemplo 3: Serializar campo repetidor
    logger.info("\n3. Serializando campo repetidor:")
    ejemplo_serializar_repetidor()
    
    # Ejemplo 4: Serializar galería
    logger.info("\n4. Serializando galería:")
    ejemplo_serializar_galeria()
    
    # Ejemplo 5: Serializar meta completo
    logger.info("\n5. Serializando meta fields completos:")
    ejemplo_serializar_meta_completo()
    
    # Ejemplo 6: Deserializar
    logger.info("\n6. Deserializando datos:")
    ejemplo_deserializar()
    
    logger.info("\n=== Fin de ejemplos ===")

if __name__ == "__main__":
    # Configurar logging para ver los resultados
    logging.basicConfig(level=logging.INFO)
    
    # Ejecutar ejemplos
    ejemplo_uso_desde_otro_servicio()
