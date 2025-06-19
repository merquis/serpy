#!/usr/bin/env python3
"""
Script para diagnosticar el problema con el formato específico
"""

import re

def debug_format():
    print("🔍 DIAGNÓSTICO DEL FORMATO")
    print("=" * 60)
    
    # El formato exacto del usuario
    test_format = "'bloques_contenido_h2', 'a:4:{s:6:\"item-0\";a:2:{s:9:\"titulo_h2\";s:13:\"primer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>primer parrafo</p>\\n\";}s:6:\"item-1\";a:2:{s:9:\"titulo_h2\";s:14:\"segundo titulo\";s:10:\"parrafo_h2\";s:23:\"<p>segundo parrafo</p>\\n\";}s:6:\"item-2\";a:2:{s:9:\"titulo_h2\";s:13:\"tercer titulo\";s:10:\"parrafo_h2\";s:22:\"<p>tercer parrafo</p>\\n\";}s:6:\"item-3\";a:2:{s:9:\"titulo_h2\";s:13:\"cuarto titulo\";s:10:\"parrafo_h2\";s:22:\"<p>cuarto parrafo</p>\\n\";}}'"
    
    print("📝 FORMATO ORIGINAL:")
    print("Longitud:", len(test_format))
    print("Primeros 100 chars:", test_format[:100])
    print("Últimos 100 chars:", test_format[-100:])
    print()
    
    print("🔍 ANÁLISIS DE CARACTERES ESPECIALES:")
    print("Contiene \\n:", '\\n' in test_format)
    print("Contiene \\\":", '\\"' in test_format)
    print("Empieza con ':", test_format.startswith("'"))
    print("Termina con ':", test_format.endswith("'"))
    print()
    
    print("🧪 PRUEBAS DE PATRONES REGEX:")
    
    # Patrón actual
    pattern1 = r"^'([^']+)',\s*'(.*)'$"
    match1 = re.match(pattern1, test_format, re.DOTALL)
    print("Patrón 1 (actual):", pattern1)
    print("¿Coincide?:", match1 is not None)
    if match1:
        print("Campo:", match1.group(1))
        print("Valor (primeros 50):", match1.group(2)[:50] + "...")
    print()
    
    # Patrón alternativo 1 - más específico
    pattern2 = r"^'([^']+)',\s*'(a:\d+:\{.*)'$"
    match2 = re.match(pattern2, test_format, re.DOTALL)
    print("Patrón 2 (específico):", pattern2)
    print("¿Coincide?:", match2 is not None)
    if match2:
        print("Campo:", match2.group(1))
        print("Valor (primeros 50):", match2.group(2)[:50] + "...")
    print()
    
    # Patrón alternativo 2 - sin anclas
    pattern3 = r"'([^']+)',\s*'(.*?)'"
    match3 = re.search(pattern3, test_format, re.DOTALL)
    print("Patrón 3 (sin anclas):", pattern3)
    print("¿Coincide?:", match3 is not None)
    if match3:
        print("Campo:", match3.group(1))
        print("Valor (primeros 50):", match3.group(2)[:50] + "...")
    print()
    
    # Análisis manual del formato
    print("🔧 ANÁLISIS MANUAL:")
    if test_format.startswith("'"):
        first_quote_end = test_format.find("'", 1)
        if first_quote_end != -1:
            field_name = test_format[1:first_quote_end]
            print("Campo extraído manualmente:", field_name)
            
            # Buscar el inicio del valor
            comma_pos = test_format.find(",", first_quote_end)
            if comma_pos != -1:
                value_start = test_format.find("'", comma_pos)
                if value_start != -1:
                    value_end = test_format.rfind("'")
                    if value_end > value_start:
                        value = test_format[value_start + 1:value_end]
                        print("Valor extraído manualmente (primeros 100):", value[:100] + "...")
                        print("Valor extraído manualmente (últimos 50):", "..." + value[-50:])
                        
                        # Verificar si el valor es PHP serializado válido
                        if value.startswith('a:') and value.endswith('}}'):
                            print("✅ El valor parece ser PHP serializado válido")
                            
                            # Probar deserialización
                            try:
                                import phpserialize
                                # Desescapar comillas
                                unescaped_value = value.replace('\\"', '"')
                                result = phpserialize.loads(unescaped_value.encode('utf-8'))
                                print("✅ Se puede deserializar correctamente")
                                print("Tipo resultado:", type(result))
                                if isinstance(result, dict):
                                    print("Claves encontradas:", list(result.keys()))
                            except Exception as e:
                                print("❌ Error deserializando:", str(e))
                        else:
                            print("❌ El valor no parece ser PHP serializado válido")

if __name__ == "__main__":
    debug_format()
