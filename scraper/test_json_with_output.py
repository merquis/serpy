"""
Prueba de la nueva función create_h2_blocks_json con salida a archivo
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.serialice_get_engine import create_h2_blocks_json
import json

# Datos de prueba
test_sections = [
    {"titulo": "primer titulo", "contenido": "primer parrafo"},
    {"titulo": "segundo titulo", "contenido": "segundo parrafo"},
    {"titulo": "tercer titulo", "contenido": "tercer parrafo"},
    {"titulo": "cuarto titulo", "contenido": "cuarto parrafo"}
]

# Generar estructura JSON
result = create_h2_blocks_json(test_sections)

# Guardar resultado en archivo
with open('test_json_output.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("Resultado guardado en test_json_output.json")

# También mostrar en consola
print("\nEstructura generada:")
print(json.dumps(result, indent=2, ensure_ascii=False))
