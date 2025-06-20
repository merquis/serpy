"""
Prueba de la nueva función create_h2_blocks_json
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serialice_get_engine import SerializeGetEngine, create_h2_blocks_json
import json

def test_json_format():
    print("=== PRUEBA DE FORMATO JSON ===\n")
    
    # Datos de prueba
    test_sections = [
        {"titulo": "primer titulo", "contenido": "primer parrafo"},
        {"titulo": "segundo titulo", "contenido": "segundo parrafo"},
        {"titulo": "tercer titulo", "contenido": "tercer parrafo"},
        {"titulo": "cuarto titulo", "contenido": "cuarto parrafo"}
    ]
    
    print("1. Datos de entrada:")
    for i, section in enumerate(test_sections):
        print(f"   - {section}")
    
    # Usar la nueva función
    print("\n2. Generando estructura JSON...")
    result = create_h2_blocks_json(test_sections)
    
    # Mostrar resultado
    print("\n3. Resultado:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Verificar estructura
    print("\n4. Verificación de estructura:")
    if "bloques_contenido_h2" in result:
        print("   ✓ Contiene clave 'bloques_contenido_h2'")
        
        bloques = result["bloques_contenido_h2"]
        print(f"   ✓ Número de items: {len(bloques)}")
        
        # Verificar cada item
        for i in range(len(test_sections)):
            key = f"item-{i}"
            if key in bloques:
                print(f"   ✓ Contiene '{key}'")
                item = bloques[key]
                if "titulo_h2" in item and "parrafo_h2" in item:
                    print(f"     - titulo_h2: {item['titulo_h2']}")
                    print(f"     - parrafo_h2: {item['parrafo_h2'].strip()}")
    else:
        print("   ✗ ERROR: No contiene clave 'bloques_contenido_h2'")
    
    # Comparar con formato serializado
    print("\n5. Comparación con formato serializado:")
    serialized_result = SerializeGetEngine.serialize_h2_blocks(test_sections)
    print(f"   Formato serializado: {serialized_result['bloques_contenido_h2'][:50]}...")
    print(f"   Formato JSON: estructura directa sin serialización PHP")

if __name__ == "__main__":
    test_json_format()
