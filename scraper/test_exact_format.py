"""
Script de prueba para verificar el formato exacto de serialización/deserialización
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serialice_get_engine import SerializeGetEngine

def test_exact_format():
    print("=== PRUEBA DE FORMATO EXACTO ===\n")
    
    # 1. Datos de prueba
    h2_sections = [
        {"titulo": "primer titulo", "contenido": "primer parrafo"},
        {"titulo": "segundo titulo", "contenido": "segundo parrafo"},
        {"titulo": "tercer titulo", "contenido": "tercer parrafo"},
        {"titulo": "cuarto titulo", "contenido": "cuarto parrafo"}
    ]
    
    print("1. Datos originales:")
    for i, section in enumerate(h2_sections):
        print(f"   - Item {i}: {section}")
    
    # 2. Serializar
    print("\n2. Serializando...")
    result = SerializeGetEngine.serialize_h2_blocks(h2_sections)
    serialized_value = result.get("bloques_contenido_h2", "")
    
    print(f"\n   Resultado completo:")
    print(f"   {serialized_value}")
    
    # 3. Verificar formato
    print("\n3. Verificando formato...")
    if serialized_value.startswith("'bloques_contenido_h2', '"):
        print("   ✓ El formato empieza correctamente con 'bloques_contenido_h2', '")
    else:
        print("   ✗ ERROR: El formato no empieza correctamente")
    
    # 4. Deserializar el resultado completo
    print("\n4. Deserializando el resultado completo...")
    deserialized = SerializeGetEngine.deserialize_php_field(serialized_value)
    
    if deserialized:
        print("   ✓ Deserialización exitosa")
        print(f"\n   Datos deserializados:")
        for key, value in deserialized.items():
            print(f"   - {key}:")
            print(f"     titulo_h2: {value.get('titulo_h2', 'N/A')}")
            print(f"     parrafo_h2: {value.get('parrafo_h2', 'N/A')}")
    else:
        print("   ✗ ERROR: No se pudo deserializar")
    
    # 5. Probar con el formato exacto proporcionado
    print("\n5. Probando con el formato exacto proporcionado...")
    test_format = "'bloques_contenido_h2', 'a:4:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:13:\"primer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>primer parrafo</p>\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:14:\"segundo titulo\";s:10:\"parrafo_h2\";s:23:\"<p>segundo parrafo</p>\n\";}s:6:\"item-2\";a:2:{s:9:\"titulo_h2\";s:13:\"tercer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>tercer parrafo</p>\n\";}s:6:\"item-3\";a:2:{s:9:\"titulo_h2\";s:13:\"cuarto titulo\";s:10:\"parrafo_h2\";s:22:\"<p>cuarto parrafo</p>\n\";}}'"
    
    print(f"   Formato de prueba: {test_format[:100]}...")
    
    # Deserializar
    deserialized_test = SerializeGetEngine.deserialize_php_field(test_format)
    
    if deserialized_test:
        print("   ✓ Formato exacto deserializado correctamente")
        print(f"\n   Contenido deserializado:")
        for key, value in deserialized_test.items():
            print(f"   - {key}: titulo='{value.get('titulo_h2', '')}', parrafo='{value.get('parrafo_h2', '').strip()}'")
    else:
        print("   ✗ ERROR: No se pudo deserializar el formato exacto")
    
    # 6. Comparar formatos
    print("\n6. Comparación de formatos:")
    print(f"   Formato generado: {serialized_value[:50]}...")
    print(f"   Formato esperado: {test_format[:50]}...")
    
    # 7. Validar ambos formatos
    print("\n7. Validación de formatos:")
    is_valid_generated = SerializeGetEngine.validate_serialized_data(serialized_value)
    is_valid_test = SerializeGetEngine.validate_serialized_data(test_format)
    
    print(f"   Formato generado válido: {'✓' if is_valid_generated else '✗'}")
    print(f"   Formato de prueba válido: {'✓' if is_valid_test else '✗'}")

if __name__ == "__main__":
    test_exact_format()
