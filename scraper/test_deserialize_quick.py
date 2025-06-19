#!/usr/bin/env python3
"""
Script para deserializar el formato del usuario
"""

from services.serialice_get_engine import SerializeGetEngine
import json
import re

def test_format():
    # El formato que envió el usuario
    test_data = '"bloques_contenido_h2":"a:8:{s:6:"item-0";a:2:{s:9:"titulo_h2";s:14:"Sostenibilidad";s:10:"parrafo_h2";s:114:"<p>Este alojamiento tiene 2 certificaciones de sostenibilidad de terceros.Más info sobre las certificaciones</p>\\n";}s:6:"item-1";a:2:{s:9:"titulo_h2";s:65:"Servicios de Hotel Faro, a Lopesan Collection Hotel - Adults Only";s:10:"parrafo_h2";s:44:"<p>¡Buenos servicios! Puntuación: 9.4</p>\\n";}s:6:"item-2";a:2:{s:9:"titulo_h2";s:17:"Normas de la casa";s:10:"parrafo_h2";s:125:"<p>Hotel Faro, a Lopesan Collection Hotel - Adults Only acepta peticiones especiales. ¡Añádelas en el siguiente paso!</p>\\n";}s:6:"item-3";a:2:{s:9:"titulo_h2";s:17:"A tener en cuenta";s:10:"parrafo_h2";s:52:"<p>Información importante sobre el alojamiento</p>\\n";}s:6:"item-4";a:2:{s:9:"titulo_h2";s:18:"Información legal";s:10:"parrafo_h2";s:363:"<p>Este alojamiento lo gestiona, autoriza o representa una empresa. Esta etiqueta no tiene ninguna importancia en términos fiscales, incluido el IVA y otros "impuestos indirectos", pero es obligatoria según la legislación europea sobre los derechos de los consumidores. Puedes encontrar más información sobre la empresa aquí:Ver los datos de la empresa</p>\\n";}s:6:"item-5";a:2:{s:9:"titulo_h2";s:43:"Comentarios auténticos de clientes reales.";s:10:"parrafo_h2";s:108:"<p>Tenemos más de 70 millones de comentarios sobre alojamientos, todosauténticos y de clientes reales</p>\\n";}s:6:"item-6";a:2:{s:9:"titulo_h2";s:17:"¿Cómo funciona?";s:10:"parrafo_h2";s:877:"<p>1 <h3 class=\\"rlp-intro-how__title rlp-intro-how__a11y-exp-title\\">Todo empieza con una reserva</h3> Todo empieza con una reserva Solo se pueden dejar comentarios si primero se ha hecho una reserva. Así es como sabemos que nuestros comentarios son de clientes reales que han estado en el alojamiento. 2 <h3 class=\\"rlp-intro-how__title rlp-intro-how__a11y-exp-title\\">Luego, un viaje</h3> Luego, un viaje Durante su estancia en el alojamiento, nuestros clientes comprueban la tranquilidad de la habitación, la amabilidad del personal y mucho más. 3 <h3 class=\\"rlp-intro-how__title rlp-intro-how__a11y-exp-title\\">Y, finalmente, un comentario</h3> Y, finalmente, un comentario Después de su viaje, los clientes nos cuentan su estancia. Comprobamos la autenticidad de los comentarios, nos aseguramos de que no haya palabras malsonantes y luego los añadimos a nuestra web.</p>\\n";}s:6:"item-7";a:2:{s:9:"titulo_h2";s:42:"Gestionar la configuración de las cookies";s:10:"parrafo_h2";s:1838:"<p>En esta web, nosotros, Booking.com y nuestros colaboradores, usamos las siguientes categorías de cookies (y tecnologías similares) que requieren tu consentimiento: cookies analíticas y cookies de marketing. <h3>Cookies analíticas</h3> Tanto nosotros como nuestros colaboradores usamos cookies analíticas para obtener información del uso que haces del sitio web, lo que a su vez se utiliza para comprender la manera en que se usa nuestra plataforma y para mejorar el rendimiento de nuestro sitio y nuestros servicios. Más información. <h3>Cookies de marketing</h3> Tanto nosotros como nuestros colaboradores usamos cookies de marketing, incluidas cookies de redes sociales, para recopilar información sobre tu comportamiento de navegación en este sitio web. Esto nos ayuda a decidir qué productos mostrarte dentro y fuera de nuestro sitio web, así como presentar y enviar contenido personalizado y anuncios en nuestra plataforma, otros sitios web y a través de mensajes push e emails. El contenido personalizado está basado en tu comportamiento de navegación y los servicios que has reservado. Estas cookies también te permiten compartir o darle a \\"me gusta\\" a páginas en redes sociales. Más información. Puedes encontrar más información sobre las cookies que usamos y el tratamiento de los datos personales en la Política de privacidad y cookies. Al hacer clic en \\"Aceptar\\", consientes que se utilicen tanto cookies analíticas como de marketing y aceptas el correspondiente tratamiento de los datos personales. Al hacer clic en \\"Rechazar\\", no tendrás una experiencia personalizada en nuestra plataforma. Puedes gestionar la configuración de las cookies y retirar tu consentimiento en cualquier momento accediendo al apartado \\"Gestionar la configuración de las cookies\\" en la parte inferior del sitio web.</p>\\n";}}"'
    
    # Extraer el valor serializado
    pattern = r'"bloques_contenido_h2"\s*:\s*"(a:\d+:\{.*)"'
    match = re.search(pattern, test_data, re.DOTALL)
    
    if match:
        serialized_value = match.group(1)
        # Limpiar el valor (quitar comillas finales)
        serialized_value = serialized_value.rstrip('"')
        
        print("🔄 Valor serializado extraído:")
        print(f"Longitud: {len(serialized_value)} caracteres")
        print(f"Empieza con: {serialized_value[:50]}...")
        print(f"Termina con: ...{serialized_value[-50:]}")
        print()
        
        # Validar
        is_valid = SerializeGetEngine.validate_serialized_data(serialized_value)
        print(f"✅ ¿Es válido? {is_valid}")
        
        if is_valid:
            # Deserializar
            result = SerializeGetEngine.deserialize_php_field(serialized_value)
            
            if result:
                print("\n📥 RESULTADO DESERIALIZADO:")
                print("=" * 50)
                
                # Convertir bytes a strings
                def convert_bytes_to_str(data):
                    if isinstance(data, bytes):
                        return data.decode('utf-8', errors='replace')
                    elif isinstance(data, dict):
                        return {convert_bytes_to_str(k): convert_bytes_to_str(v) for k, v in data.items()}
                    elif isinstance(data, list):
                        return [convert_bytes_to_str(item) for item in data]
                    else:
                        return data
                
                result = convert_bytes_to_str(result)
                
                # Mostrar como JSON formateado
                json_result = json.dumps(result, ensure_ascii=False, indent=2)
                print(json_result)
                
                print("\n📋 RESUMEN:")
                print(f"Total de bloques: {len(result)}")
                for key, value in result.items():
                    if isinstance(value, dict) and 'titulo_h2' in value:
                        print(f"• {key}: {value['titulo_h2']}")
            else:
                print("❌ No se pudo deserializar")
        else:
            print("❌ El valor no es PHP serializado válido")
    else:
        print("❌ No se pudo extraer el valor serializado")

if __name__ == "__main__":
    test_format()
