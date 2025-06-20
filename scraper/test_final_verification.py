"""
Verificación final del formato exacto de serialización/deserialización
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serialice_get_engine import SerializeGetEngine

def test_final():
    print("=== VERIFICACIÓN FINAL ===\n")
    
    # 1. Probar deserialización del formato exacto proporcionado
    print("1. DESERIALIZACIÓN DEL FORMATO EXACTO:")
    exact_format = "'bloques_contenido_h2', 'a:4:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:13:\"primer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>primer parrafo</p>\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:14:\"segundo titulo\";s:10:\"parrafo_h2\";s:23:\"<p>segundo parrafo</p>\n\";}s:6:\"item-2\";a:2:{s:9:\"titulo_h2\";s:13:\"tercer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>tercer parrafo</p>\n\";}s:6:\"item-3\";a:2:{s:9:\"titulo_h2\";s:13:\"cuarto titulo\";s:10:\"parrafo_h2\";s:22:\"<p>cuarto parrafo</p>\n\";}}'"
    
    print(f"Formato de entrada: {exact_format[:80]}...")
    
    # Deserializar
    result = SerializeGetEngine.deserialize_php_field(exact_format)
    
    if result and isinstance(result, dict):
        print("✅ Deserialización exitosa!")
        print(f"Número de items: {len(result)}")
        
        # Mostrar contenido
        for key, value in result.items():
            if isinstance(value, dict):
                titulo = value.get('titulo_h2', 'N/A')
                parrafo = value.get('parrafo_h2', 'N/A').strip()
                print(f"\n{key}:")
                print(f"  - titulo_h2: {titulo}")
                print(f"  - parrafo_h2: {parrafo}")
    else:
        print("❌ Error en la deserialización")
        print(f"Resultado: {result}")
    
    # 2. Probar serialización
    print("\n\n2. SERIALIZACIÓN:")
    test_data = [
        {"titulo": "primer titulo", "contenido": "primer parrafo"},
        {"titulo": "segundo titulo", "contenido": "segundo parrafo"},
        {"titulo": "tercer titulo", "contenido": "tercer parrafo"},
        {"titulo": "cuarto titulo", "contenido": "cuarto parrafo"}
    ]
    
    result = SerializeGetEngine.serialize_h2_blocks(test_data)
    serialized = result.get("bloques_contenido_h2", "")
    
    print(f"Resultado serializado: {serialized[:80]}...")
    
    # Verificar formato
    checks = {
        "Empieza con 'bloques_contenido_h2', '": serialized.startswith("'bloques_contenido_h2', '"),
        "Termina con comilla simple": serialized.endswith("'"),
        "Contiene comillas escapadas": '\\"' in serialized
    }
    
    print("\nVerificaciones:")
    for check, result in checks.items():
        print(f"  - {check}: {'✅' if result else '❌'}")
    
    # 3. Ciclo completo
    print("\n\n3. CICLO COMPLETO (Serializar → Deserializar):")
    
    # Deserializar el resultado serializado
    deserialized_again = SerializeGetEngine.deserialize_php_field(serialized)
    
    if deserialized_again and isinstance(deserialized_again, dict):
        print("✅ Ciclo completo exitoso!")
        print(f"Items recuperados: {len(deserialized_again)}")
    else:
        print("❌ Error en el ciclo completo")
    
    # 4. Validación
    print("\n\n4. VALIDACIÓN:")
    is_valid_exact = SerializeGetEngine.validate_serialized_data(exact_format)
    is_valid_generated = SerializeGetEngine.validate_serialized_data(serialized)
    
    print(f"Formato exacto proporcionado válido: {'✅' if is_valid_exact else '❌'}")
    print(f"Formato generado válido: {'✅' if is_valid_generated else '❌'}")
    
    print("\n=== FIN DE LA VERIFICACIÓN ===")

if __name__ == "__main__":
    test_final()
