"""
Ejemplo de uso de la nueva función create_h2_blocks_json
"""
from services.serialice_get_engine import create_h2_blocks_json
import json

# Ejemplo 1: Datos simples
print("=== EJEMPLO 1: Datos simples ===")
datos_simples = [
    {"titulo": "Ubicación", "contenido": "En el centro de la ciudad"},
    {"titulo": "Servicios", "contenido": "WiFi, Piscina, Gimnasio"}
]

resultado1 = create_h2_blocks_json(datos_simples)
print(json.dumps(resultado1, indent=2, ensure_ascii=False))

# Ejemplo 2: Datos con HTML
print("\n=== EJEMPLO 2: Datos con HTML ===")
datos_html = [
    {"titulo": "Descripción", "contenido": "<p>Hotel de lujo con vistas al mar</p>"},
    {"titulo": "Habitaciones", "contenido": "<h3>Suite Deluxe</h3>Amplia habitación con balcón"}
]

resultado2 = create_h2_blocks_json(datos_html)
print(json.dumps(resultado2, indent=2, ensure_ascii=False))

# Ejemplo 3: Estructura esperada
print("\n=== ESTRUCTURA ESPERADA ===")
print("""
{
  "bloques_contenido_h2": {
    "item-0": {
      "titulo_h2": "primer titulo",
      "parrafo_h2": "<p>primer parrafo</p>\\n"
    },
    "item-1": {
      "titulo_h2": "segundo titulo", 
      "parrafo_h2": "<p>segundo parrafo</p>\\n"
    }
  }
}
""")

# Uso en código
print("\n=== USO EN CÓDIGO ===")
print("""
from services.serialice_get_engine import create_h2_blocks_json

# Tus datos
h2_sections = [
    {"titulo": "Título 1", "contenido": "Contenido 1"},
    {"titulo": "Título 2", "contenido": "Contenido 2"}
]

# Generar estructura JSON
resultado = create_h2_blocks_json(h2_sections)

# El resultado tendrá la estructura:
# {
#   "bloques_contenido_h2": {
#     "item-0": {"titulo_h2": "...", "parrafo_h2": "..."},
#     "item-1": {"titulo_h2": "...", "parrafo_h2": "..."}
#   }
# }
""")
