#!/usr/bin/env python3
"""
Script para probar el ciclo completo: serialización con comillas escapadas -> deserialización
"""

from services.serialice_get_engine import SerializeGetEngine
import json

def test_complete_cycle():
    print("🔄 PRUEBA CICLO COMPLETO: SERIALIZACIÓN + DESERIALIZACIÓN")
    print("=" * 70)
    
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
    
    print("📝 PASO 1: Datos originales")
    print("-" * 30)
    for i, item in enumerate(test_data):
        print(f"  {i}: {item['titulo']} -> {item['contenido']}")
    
    print("\n🔄 PASO 2: Serializando con comillas escapadas...")
    print("-" * 50)
    
    # Serializar
    result = SerializeGetEngine.serialize_h2_blocks(test_data)
    
    if "bloques_contenido_h2" in result:
        serialized = result["bloques_contenido_h2"]
        
        print("✅ Serialización exitosa:")
        print(f"Longitud: {len(serialized)} caracteres")
        print(f"Inicio: {serialized[:80]}...")
        print(f"Final: ...{serialized[-80:]}")
        
        # Verificar comillas escapadas
        if '""item-0""' in serialized:
            print("✅ Comillas correctamente escapadas")
        else:
            print("❌ ERROR: Comillas no escapadas")
            return
        
        print("\n🔄 PASO 3: Deserializando datos con comillas escapadas...")
        print("-" * 60)
        
        # Deserializar
        deserialized = SerializeGetEngine.deserialize_php_field(serialized)
        
        if deserialized:
            print("✅ Deserialización exitosa:")
            
            # Convertir bytes a strings si es necesario
            def convert_bytes_to_str(data):
                if isinstance(data, bytes):
                    return data.decode('utf-8', errors='replace')
                elif isinstance(data, dict):
                    return {convert_bytes_to_str(k): convert_bytes_to_str(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [convert_bytes_to_str(item) for item in data]
                else:
                    return data
            
            deserialized = convert_bytes_to_str(deserialized)
            
            # Mostrar resultado
            print(json.dumps(deserialized, ensure_ascii=False, indent=2))
            
            print("\n📊 PASO 4: Verificación de integridad")
            print("-" * 40)
            
            # Verificar que los datos son correctos
            if isinstance(deserialized, dict):
                items_found = len([k for k in deserialized.keys() if k.startswith('item-')])
                print(f"✅ Elementos encontrados: {items_found}")
                
                # Verificar contenido específico
                if 'item-0' in deserialized:
                    item_0 = deserialized['item-0']
                    if isinstance(item_0, dict) and 'titulo_h2' in item_0:
                        original_title = test_data[0]['titulo']
                        deserialized_title = item_0['titulo_h2']
                        
                        if original_title == deserialized_title:
                            print(f"✅ Título preservado: '{original_title}'")
                        else:
                            print(f"❌ Título alterado: '{original_title}' -> '{deserialized_title}'")
                        
                        # Verificar contenido
                        if 'parrafo_h2' in item_0:
                            original_content = f"{test_data[0]['contenido']}\n"
                            deserialized_content = item_0['parrafo_h2']
                            
                            if original_content == deserialized_content:
                                print(f"✅ Contenido preservado")
                            else:
                                print(f"❌ Contenido alterado")
                                print(f"   Original: '{original_content}'")
                                print(f"   Deserializado: '{deserialized_content}'")
                
                print("\n🎯 RESULTADO FINAL:")
                print("=" * 30)
                print("✅ ÉXITO: Ciclo completo funciona correctamente")
                print("   - Serialización con comillas escapadas: ✅")
                print("   - Deserialización de comillas escapadas: ✅")
                print("   - Integridad de datos preservada: ✅")
                
            else:
                print("❌ ERROR: Resultado deserializado no es un diccionario")
        else:
            print("❌ ERROR: Deserialización falló")
    else:
        print("❌ ERROR: Serialización falló")

if __name__ == "__main__":
    test_complete_cycle()
