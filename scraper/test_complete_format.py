"""
Prueba completa del formato exacto de serialización/deserialización
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serialice_get_engine import SerializeGetEngine

def test_complete_cycle():
    print("=== PRUEBA COMPLETA DE SERIALIZACIÓN Y DESERIALIZACIÓN ===\n")
    
    # 1. Datos de prueba
    test_sections = [
        {"titulo": "primer titulo", "contenido": "primer parrafo"},
        {"titulo": "segundo titulo", "contenido": "segundo parrafo"},
        {"titulo": "tercer titulo", "contenido": "tercer parrafo"},
        {"titulo": "cuarto titulo", "contenido": "cuarto parrafo"}
    ]
    
    print("1. DATOS ORIGINALES:")
    for i, section in enumerate(test_sections):
        print(f"   Item {i}: {section}")
    
    # 2. Serializar
    print("\n2. SERIALIZANDO...")
    result = SerializeGetEngine.serialize_h2_blocks(test_sections)
    serialized = result.get("bloques_contenido_h2", "")
    
    print(f"\n   Resultado serializado:")
    print(f"   {serialized}")
    
    # 3. Verificar formato
    print("\n3. VERIFICANDO FORMATO:")
    
    # Debe empezar con 'bloques_contenido_h2',
    if serialized.startswith("'bloques_contenido_h2', '"):
        print("   ✓ Empieza correctamente con 'bloques_contenido_h2', '")
    else:
        print("   ✗ ERROR: No empieza con el formato correcto")
    
    # Debe terminar con comilla simple
    if serialized.endswith("'"):
        print("   ✓ Termina correctamente con comilla simple")
    else:
        print("   ✗ ERROR: No termina con comilla simple")
    
    # Debe tener comillas escapadas
    if '\\"' in serialized:
        print("   ✓ Contiene comillas escapadas correctamente")
    else:
        print("   ✗ ERROR: No contiene comillas escapadas")
    
    # 4. Deserializar
    print("\n4. DESERIALIZANDO...")
    deserialized = SerializeGetEngine.deserialize_php_field(serialized)
    
    if deserialized:
        print("   ✓ Deserialización exitosa")
        print("\n   Datos deserializados:")
        for key, value in deserialized.items():
            print(f"   {key}:")
            print(f"     - titulo_h2: {value.get('titulo_h2', 'N/A')}")
            print(f"     - parrafo_h2: {value.get('parrafo_h2', 'N/A').strip()}")
    else:
        print("   ✗ ERROR: No se pudo deserializar")
    
    # 5. Probar con el formato exacto proporcionado
    print("\n5. PROBANDO CON FORMATO EXACTO PROPORCIONADO:")
    exact_format = "'bloques_contenido_h2', 'a:4:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:13:\"primer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>primer parrafo</p>\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:14:\"segundo titulo\";s:10:\"parrafo_h2\";s:23:\"<p>segundo parrafo</p>\n\";}s:6:\"item-2\";a:2:{s:9:\"titulo_h2\";s:13:\"tercer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>tercer parrafo</p>\n\";}s:6:\"item-3\";a:2:{s:9:\"titulo_h2\";s:13:\"cuarto titulo\";s:10:\"parrafo_h2\";s:22:\"<p>cuarto parrafo</p>\n\";}}'"
    
    print(f"   Formato exacto (primeros 100 caracteres):")
    print(f"   {exact_format[:100]}...")
    
    # Deserializar formato exacto
    exact_deserialized = SerializeGetEngine.deserialize_php_field(exact_format)
    
    if exact_deserialized:
        print("\n   ✓ Formato exacto deserializado correctamente")
        items_count = len(exact_deserialized)
        print(f"   Número de items: {items_count}")
    else:
        print("\n   ✗ ERROR: No se pudo deserializar el formato exacto")
    
    # 6. Comparar formatos
    print("\n6. COMPARACIÓN DE FORMATOS:")
    print(f"   Generado (primeros 50): {serialized[:50]}...")
    print(f"   Esperado (primeros 50): {exact_format[:50]}...")
    
    # 7. Validación
    print("\n7. VALIDACIÓN:")
    is_valid_generated = SerializeGetEngine.validate_serialized_data(serialized)
    is_valid_exact = SerializeGetEngine.validate_serialized_data(exact_format)
    
    print(f"   Formato generado válido: {'✓' if is_valid_generated else '✗'}")
    print(f"   Formato exacto válido: {'✓' if is_valid_exact else '✗'}")

if __name__ == "__main__":
    test_complete_cycle()
