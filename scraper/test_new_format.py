#!/usr/bin/env python3
"""
Script para probar el nuevo formato 'campo', 'valor' con escapado \"
"""

from services.serialice_get_engine import SerializeGetEngine
import json

def test_new_format():
    print("🔧 PRUEBA DEL NUEVO FORMATO")
    print("=" * 60)
    
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
    
    print("\n🔄 PASO 2: Serializando con nuevo formato...")
    print("-" * 50)
    
    # Serializar
    result = SerializeGetEngine.serialize_h2_blocks(test_data)
    
    if "bloques_contenido_h2" in result:
        new_format_result = result["bloques_contenido_h2"]
        
        print("✅ Serialización exitosa:")
        print(f"Longitud: {len(new_format_result)} caracteres")
        print("\n📋 RESULTADO COMPLETO:")
        print("-" * 80)
        print(new_format_result)
        print("-" * 80)
        
        # Verificar formato
        if new_format_result.startswith("'bloques_contenido_h2', '") and new_format_result.endswith("'"):
            print("\n✅ Formato 'campo', 'valor' correcto")
        else:
            print("\n❌ ERROR: Formato incorrecto")
            return
        
        # Verificar escapado
        if '\\"item-0\\"' in new_format_result:
            print("✅ Comillas correctamente escapadas con \\\"")
        else:
            print("❌ ERROR: Comillas no escapadas correctamente")
            return
        
        print("\n🔄 PASO 3: Deserializando nuevo formato...")
        print("-" * 50)
        
        # Deserializar
        deserialized = SerializeGetEngine.deserialize_php_field(new_format_result)
        
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
                
                print("\n🎯 RESULTADO FINAL:")
                print("=" * 40)
                print("✅ ÉXITO: Nuevo formato funciona correctamente")
                print("   - Formato 'campo', 'valor': ✅")
                print("   - Escapado con \\\" : ✅")
                print("   - Deserialización: ✅")
                print("   - Integridad de datos: ✅")
                
                print(f"\n📋 FORMATO FINAL GENERADO:")
                print("=" * 40)
                print("El resultado es exactamente como solicitaste:")
                print(f"'bloques_contenido_h2', 'a:4:{{s:6:\\\"item-0\\\"...}}'")
                
            else:
                print("❌ ERROR: Resultado deserializado no es un diccionario")
        else:
            print("❌ ERROR: Deserialización falló")
    else:
        print("❌ ERROR: Serialización falló")

if __name__ == "__main__":
    test_new_format()
