"""
Test para verificar que la serialización funciona correctamente
"""
from serialice_get_engine import SerializeGetEngine
import json

# Datos de prueba similares a los que se extraen de Booking
test_h2_sections = [
    {
        "titulo": "Sostenibilidad",
        "contenido": "<p>Este alojamiento tiene 1 certificación de sostenibilidad de terceros.Más info sobre las certificaciones</p>"
    },
    {
        "titulo": "Servicios del resort The Ritz-Carlton Tenerife, Abama",
        "contenido": "<p>¡Buenos servicios! Puntuación: 9.2</p>"
    },
    {
        "titulo": "Normas de la casa",
        "contenido": "<p>The Ritz-Carlton Tenerife, Abama acepta peticiones especiales. ¡Añádelas en el siguiente paso!</p>"
    },
    {
        "titulo": "A tener en cuenta",
        "contenido": "<p>Información importante sobre el alojamiento</p>"
    },
    {
        "titulo": "Información legal",
        "contenido": "<p>Este alojamiento lo gestiona, autoriza o representa una empresa. Esta etiqueta no tiene ninguna importancia en términos fiscales, incluido el IVA y otros \"impuestos indirectos\", pero es obligatoria según la legislación europea sobre los derechos de los consumidores. Puedes encontrar más información sobre la empresa aquí:Ver los datos de la empresa</p>"
    },
    {
        "titulo": "Comentarios auténticos de clientes reales.",
        "contenido": "<p>Tenemos más de 70 millones de comentarios sobre alojamientos, todosauténticos y de clientes reales</p>"
    },
    {
        "titulo": "¿Cómo funciona?",
        "contenido": "<p>1 <h3 class=\"rlp-intro-how__title rlp-intro-how__a11y-exp-title\">Todo empieza con una reserva</h3> Todo empieza con una reserva Solo se pueden dejar comentarios si primero se ha hecho una reserva. Así es como sabemos que nuestros comentarios son de clientes reales que han estado en el alojamiento. 2 <h3 class=\"rlp-intro-how__title rlp-intro-how__a11y-exp-title\">Luego, un viaje</h3> Luego, un viaje Durante su estancia en el alojamiento, nuestros clientes comprueban la tranquilidad de la habitación, la amabilidad del personal y mucho más. 3 <h3 class=\"rlp-intro-how__title rlp-intro-how__a11y-exp-title\">Y, finalmente, un comentario</h3> Y, finalmente, un comentario Después de su viaje, los clientes nos cuentan su estancia. Comprobamos la autenticidad de los comentarios, nos aseguramos de que no haya palabras malsonantes y luego los añadimos a nuestra web.</p>"
    },
    {
        "titulo": "Gestionar la configuración de las cookies",
        "contenido": "<p>En esta web, nosotros, Booking.com y nuestros colaboradores, usamos las siguientes categorías de cookies (y tecnologías similares) que requieren tu consentimiento: cookies analíticas y cookies de marketing. <h3>Cookies analíticas</h3> Tanto nosotros como nuestros colaboradores usamos cookies analíticas para obtener información del uso que haces del sitio web, lo que a su vez se utiliza para comprender la manera en que se usa nuestra plataforma y para mejorar el rendimiento de nuestro sitio y nuestros servicios. Más información. <h3>Cookies de marketing</h3> Tanto nosotros como nuestros colaboradores usamos cookies de marketing, incluidas cookies de redes sociales, para recopilar información sobre tu comportamiento de navegación en este sitio web. Esto nos ayuda a decidir qué productos mostrarte dentro y fuera de nuestro sitio web, así como presentar y enviar contenido personalizado y anuncios en nuestra plataforma, otros sitios web y a través de mensajes push e emails. El contenido personalizado está basado en tu comportamiento de navegación y los servicios que has reservado. Estas cookies también te permiten compartir o darle a \"me gusta\" a páginas en redes sociales. Más información. Puedes encontrar más información sobre las cookies que usamos y el tratamiento de los datos personales en la Política de privacidad y cookies. Al hacer clic en \"Aceptar\", consientes que se utilicen tanto cookies analíticas como de marketing y aceptas el correspondiente tratamiento de los datos personales. Al hacer clic en \"Rechazar\", no tendrás una experiencia personalizada en nuestra plataforma. Puedes gestionar la configuración de las cookies y retirar tu consentimiento en cualquier momento accediendo al apartado \"Gestionar la configuración de las cookies\" en la parte inferior del sitio web.</p>"
    }
]

def test_serialization():
    print("🧪 Probando serialización de bloques H2...")
    
    # Serializar usando SerializeGetEngine
    result = SerializeGetEngine.serialize_h2_blocks(test_h2_sections)
    
    print(f"✅ Resultado de serialización:")
    print(f"Claves: {list(result.keys())}")
    
    serialized_value = result.get("bloques_contenido_h2", "")
    print(f"📏 Longitud del valor serializado: {len(serialized_value)} caracteres")
    
    # Mostrar inicio y final del valor serializado
    if serialized_value:
        print(f"🔍 Inicio (primeros 100 chars): {serialized_value[:100]}")
        print(f"🔍 Final (últimos 100 chars): {serialized_value[-100:]}")
        
        # Verificar que termina correctamente
        if serialized_value.endswith('}}'):
            print("✅ El valor serializado termina correctamente con '}}'")
        else:
            print(f"❌ El valor serializado NO termina correctamente. Termina con: '{serialized_value[-10:]}'")
        
        # Validar que es serialización PHP válida
        is_valid = SerializeGetEngine.validate_serialized_data(serialized_value)
        print(f"🔍 ¿Es serialización PHP válida?: {is_valid}")
        
        if is_valid:
            # Intentar deserializar para verificar
            deserialized = SerializeGetEngine.deserialize_php_field(serialized_value)
            print(f"✅ Deserialización exitosa. Elementos: {len(deserialized) if isinstance(deserialized, dict) else 'N/A'}")
        else:
            print("❌ La serialización no es válida")
    
    # Crear un JSON de prueba como el que se genera en Booking
    test_json = {
        "title": "The Ritz-Carlton Tenerife, Abama - Lujo exclusivo en Guía de Isora",
        "slug": "the-ritz-carlton-tenerife-abama-lujo-exclusivo-en-guia-de-isora",
        "status": "publish",
        "content": "<p>The Ritz-Carlton Tenerife, Abama es un alojamiento destacado en Guía de Isora.</p>",
        "featured_media": 0,
        "parent": 0,
        "template": "",
        "meta": {
            "fecha_scraping": "2025-06-19T17:54:33.479195+00:00",
            "busqueda_checkin": "2025-06-19",
            "busqueda_checkout": "2025-06-20",
            "busqueda_adultos": "2",
            "busqueda_ninos": "",
            "busqueda_habitaciones": "1",
            "nombre_alojamiento": "The Ritz-Carlton Tenerife, Abama",
            "tipo_alojamiento": "hotel",
            "titulo_h1": "The Ritz-Carlton Tenerife, Abama",
            **result,  # Aquí se incluye el bloques_contenido_h2 serializado
        }
    }
    
    print(f"\n📄 JSON de prueba generado:")
    json_str = json.dumps(test_json, ensure_ascii=False, indent=2)
    print(f"📏 Longitud total del JSON: {len(json_str)} caracteres")
    
    # Verificar que el JSON se puede parsear correctamente
    try:
        parsed_json = json.loads(json_str)
        print("✅ JSON válido y parseable")
        
        # Verificar que el campo serializado está completo en el JSON
        meta_bloques = parsed_json.get("meta", {}).get("bloques_contenido_h2", "")
        if meta_bloques == serialized_value:
            print("✅ El campo serializado se mantiene íntegro en el JSON")
        else:
            print("❌ El campo serializado se ha modificado en el JSON")
            print(f"Original: {len(serialized_value)} chars")
            print(f"En JSON: {len(meta_bloques)} chars")
            
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
    
    return result

if __name__ == "__main__":
    test_serialization()
