"""
Prueba específica del problema de deserialización
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serialice_get_engine import SerializeGetEngine

# El formato exacto que proporcionaste
test_data = "'bloques_contenido_h2', 'a:4:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:13:\"primer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>primer parrafo</p>\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:14:\"segundo titulo\";s:10:\"parrafo_h2\";s:23:\"<p>segundo parrafo</p>\n\";}s:6:\"item-2\";a:2:{s:9:\"titulo_h2\";s:13:\"tercer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>tercer parrafo</p>\n\";}s:6:\"item-3\";a:2:{s:9:\"titulo_h2\";s:13:\"cuarto titulo\";s:10:\"parrafo_h2\";s:22:\"<p>cuarto parrafo</p>\n\";}}'"

print("=== PRUEBA DE DESERIALIZACIÓN DEL FORMATO EXACTO ===\n")
print(f"Datos de entrada (primeros 100 caracteres):\n{test_data[:100]}...\n")

try:
    # Intentar deserializar
    result = SerializeGetEngine.deserialize_php_field(test_data)
    
    if result:
        print("✅ ÉXITO: Deserialización completada\n")
        print("Datos deserializados:")
        
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"\n{key}:")
                if isinstance(value, dict):
                    print(f"  - titulo_h2: {value.get('titulo_h2', 'N/A')}")
                    print(f"  - parrafo_h2: {value.get('parrafo_h2', 'N/A').strip()}")
                else:
                    print(f"  - {value}")
        else:
            print(result)
    else:
        print("❌ ERROR: La deserialización devolvió un resultado vacío")
        
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()

# También probar la validación
print("\n=== VALIDACIÓN ===")
is_valid = SerializeGetEngine.validate_serialized_data(test_data)
print(f"¿Es válido el formato? {'✅ SÍ' if is_valid else '❌ NO'}")

# Probar serialización inversa
print("\n=== SERIALIZACIÓN INVERSA ===")
test_sections = [
    {"titulo": "primer titulo", "contenido": "primer parrafo"},
    {"titulo": "segundo titulo", "contenido": "segundo parrafo"},
    {"titulo": "tercer titulo", "contenido": "tercer parrafo"},
    {"titulo": "cuarto titulo", "contenido": "cuarto parrafo"}
]

result = SerializeGetEngine.serialize_h2_blocks(test_sections)
serialized = result.get("bloques_contenido_h2", "")
print(f"Resultado serializado (primeros 100 caracteres):\n{serialized[:100]}...")

# Comparar
print("\n=== COMPARACIÓN ===")
print(f"Original empieza con: {test_data[:50]}")
print(f"Generado empieza con: {serialized[:50]}")
