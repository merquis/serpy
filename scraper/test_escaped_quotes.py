#!/usr/bin/env python3
"""
Script para probar el escapado de comillas en la serialización
"""

from services.serialice_get_engine import SerializeGetEngine
import json

def test_escaped_quotes():
    print("🔧 PRUEBA DE ESCAPADO DE COMILLAS")
    print("=" * 50)
    
    # Datos de prueba
    test_data = [
        {
            "titulo": "primer titulo",
            "contenido": "<p>primer parrafo</p>"
        },
        {
            "titulo": "segundo titulo", 
            "contenido": "<p>segundo parrafo</p>"
        },
        {
            "titulo": "tercer titulo",
            "contenido": "<p>tercer parrafo</p>"
        },
        {
            "titulo": "cuarto titulo",
            "contenido": "<p>cuarto parrafo</p>"
        }
    ]
    
    print("📝 Datos de entrada:")
    for i, item in enumerate(test_data):
        print(f"  {i}: {item['titulo']} -> {item['contenido']}")
    
    print("\n🔄 Serializando con comillas escapadas...")
    
    # Serializar
    result = SerializeGetEngine.serialize_h2_blocks(test_data)
    
    if "bloques_contenido_h2" in result:
        serialized = result["bloques_contenido_h2"]
        
        print("\n✅ RESULTADO CON COMILLAS ESCAPADAS:")
        print("-" * 50)
        print(serialized)
        print("-" * 50)
        
        # Verificar que las comillas están escapadas
        if '""item-0""' in serialized and '""titulo_h2""' in serialized:
            print("\n🎯 ✅ ÉXITO: Las comillas están correctamente escapadas")
            print("   - Encontrado: \"\"item-0\"\"")
            print("   - Encontrado: \"\"titulo_h2\"\"")
        else:
            print("\n❌ ERROR: Las comillas NO están escapadas correctamente")
            
        # Contar elementos
        item_count = serialized.count('""item-')
        print(f"\n📊 Elementos encontrados: {item_count}")
        
        # Mostrar primeros caracteres para verificar formato
        print(f"\n🔍 Inicio: {serialized[:100]}...")
        print(f"🔍 Final: ...{serialized[-100:]}")
        
    else:
        print("❌ ERROR: No se generó el campo bloques_contenido_h2")

if __name__ == "__main__":
    test_escaped_quotes()
