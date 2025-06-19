"""
Prueba con logging a archivo
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serialice_get_engine import SerializeGetEngine

# Abrir archivo de log
with open('test_results.log', 'w', encoding='utf-8') as log:
    # El formato exacto que proporcionaste
    test_data = "'bloques_contenido_h2', 'a:4:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:13:\"primer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>primer parrafo</p>\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:14:\"segundo titulo\";s:10:\"parrafo_h2\";s:23:\"<p>segundo parrafo</p>\n\";}s:6:\"item-2\";a:2:{s:9:\"titulo_h2\";s:13:\"tercer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>tercer parrafo</p>\n\";}s:6:\"item-3\";a:2:{s:9:\"titulo_h2\";s:13:\"cuarto titulo\";s:10:\"parrafo_h2\";s:22:\"<p>cuarto parrafo</p>\n\";}}'"
    
    log.write("=== PRUEBA DE DESERIALIZACIÓN ===\n\n")
    log.write(f"Datos de entrada:\n{test_data}\n\n")
    
    try:
        # Intentar deserializar
        result = SerializeGetEngine.deserialize_php_field(test_data)
        
        if result:
            log.write("✅ ÉXITO: Deserialización completada\n\n")
            log.write("Datos deserializados:\n")
            
            if isinstance(result, dict):
                for key, value in result.items():
                    log.write(f"\n{key}:\n")
                    if isinstance(value, dict):
                        log.write(f"  - titulo_h2: {value.get('titulo_h2', 'N/A')}\n")
                        log.write(f"  - parrafo_h2: {value.get('parrafo_h2', 'N/A').strip()}\n")
                    else:
                        log.write(f"  - {value}\n")
            else:
                log.write(str(result) + "\n")
        else:
            log.write("❌ ERROR: La deserialización devolvió un resultado vacío\n")
            
    except Exception as e:
        log.write(f"❌ ERROR: {type(e).__name__}: {str(e)}\n")
        import traceback
        traceback.print_exc(file=log)
    
    # También probar la validación
    log.write("\n=== VALIDACIÓN ===\n")
    is_valid = SerializeGetEngine.validate_serialized_data(test_data)
    log.write(f"¿Es válido el formato? {'✅ SÍ' if is_valid else '❌ NO'}\n")
    
    # Probar serialización
    log.write("\n=== SERIALIZACIÓN ===\n")
    test_sections = [
        {"titulo": "primer titulo", "contenido": "primer parrafo"},
        {"titulo": "segundo titulo", "contenido": "segundo parrafo"},
        {"titulo": "tercer titulo", "contenido": "tercer parrafo"},
        {"titulo": "cuarto titulo", "contenido": "cuarto parrafo"}
    ]
    
    result = SerializeGetEngine.serialize_h2_blocks(test_sections)
    serialized = result.get("bloques_contenido_h2", "")
    log.write(f"Resultado serializado:\n{serialized}\n")
    
    # Comparar
    log.write("\n=== COMPARACIÓN ===\n")
    log.write(f"Original: {test_data[:100]}...\n")
    log.write(f"Generado: {serialized[:100]}...\n")

print("Prueba completada. Revisa el archivo test_results.log")
