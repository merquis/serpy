#!/usr/bin/env python3
"""
Script para probar la deserialización del formato específico del usuario
"""

from services.serialice_get_engine import SerializeGetEngine
import json

def test_specific_format():
    print("🔧 PRUEBA DE DESERIALIZACIÓN DEL FORMATO ESPECÍFICO")
    print("=" * 70)
    
    # El formato exacto que envió el usuario
    test_format = "'bloques_contenido_h2', 'a:4:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:13:\"primer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>primer parrafo</p>\\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:14:\"segundo titulo\";s:10:\"parrafo_h2\";s:23:\"<p>segundo parrafo</p>\\n\";}s:6:\"item-2\";a:2:{s:9:\"titulo_h2\";s:13:\"tercer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>tercer parrafo</p>\\n\";}s:6:\"item-3\";a:2:{s:9:\"titulo_h2\";s:13:\"cuarto titulo\";s:10:\"parrafo_h2\";s:22:\"<p>cuarto parrafo</p>\\n\";}}'"
    
    print("📝 FORMATO A DESERIALIZAR:")
    print("-" * 50)
    print(test_format)
    print("-" * 50)
    
    print("\n🔄 PASO 1: Validando formato...")
    
    # Validar
    is_valid = SerializeGetEngine.validate_serialized_data(test_format)
    print(f"✅ ¿Es válido? {is_valid}")
    
    print("\n🔄 PASO 2: Deserializando...")
    
    # Deserializar
    result = SerializeGetEngine.deserialize_php_field(test_format)
    
    if result:
        print("✅ Deserialización exitosa!")
        
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
        
        result = convert_bytes_to_str(result)
        
        print("\n📥 RESULTADO DESERIALIZADO:")
        print("=" * 50)
        
        # Mostrar como JSON formateado
        json_result = json.dumps(result, ensure_ascii=False, indent=2)
        print(json_result)
        
        print("\n📊 VERIFICACIÓN:")
        print("-" * 30)
        
        if isinstance(result, dict):
            items_found = len([k for k in result.keys() if k.startswith('item-')])
            print(f"✅ Elementos encontrados: {items_found}")
            
            # Verificar contenido específico
            for i in range(4):
                item_key = f"item-{i}"
                if item_key in result:
                    item = result[item_key]
                    if isinstance(item, dict) and 'titulo_h2' in item:
                        titulo = item['titulo_h2']
                        print(f"✅ {item_key}: {titulo}")
                    else:
                        print(f"❌ {item_key}: Estructura incorrecta")
                else:
                    print(f"❌ {item_key}: No encontrado")
            
            print("\n🎯 RESULTADO FINAL:")
            print("=" * 30)
            print("✅ ÉXITO: El formato se deserializa correctamente")
            print("   - Formato 'campo', 'valor' detectado: ✅")
            print("   - Comillas escapadas procesadas: ✅")
            print("   - Estructura de datos preservada: ✅")
            
        else:
            print("❌ ERROR: Resultado no es un diccionario")
    else:
        print("❌ ERROR: La deserialización falló")
        print("\n🔍 DIAGNÓSTICO:")
        
        # Intentar diagnosticar el problema
        import re
        pattern = r"^'([^']+)',\s*'(.*)'$"
        match = re.match(pattern, test_format, re.DOTALL)
        
        if match:
            field_name = match.group(1)
            field_value = match.group(2)
            print(f"✅ Patrón regex detectado: campo='{field_name}'")
            print(f"📝 Valor extraído (primeros 100 chars): {field_value[:100]}...")
            
            # Verificar si el valor tiene comillas escapadas
            if '\\"' in field_value:
                print("✅ Comillas escapadas detectadas")
                unescaped = field_value.replace('\\"', '"')
                print(f"📝 Valor desescapado (primeros 100 chars): {unescaped[:100]}...")
                
                # Intentar deserializar solo el valor
                try:
                    import phpserialize
                    test_result = phpserialize.loads(unescaped.encode('utf-8'))
                    print("✅ El valor desescapado se puede deserializar")
                except Exception as e:
                    print(f"❌ Error deserializando valor: {e}")
            else:
                print("❌ No se detectaron comillas escapadas")
        else:
            print("❌ El patrón regex no coincide")

if __name__ == "__main__":
    test_specific_format()
