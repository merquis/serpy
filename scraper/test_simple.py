import sys
print("Python version:", sys.version)

try:
    import phpserialize
    print("phpserialize importado correctamente")
except ImportError as e:
    print("Error importando phpserialize:", e)

# Prueba directa de deserialización
test_data = 'a:4:{s:6:"item-0";a:2:{s:9:"titulo_h2";s:13:"primer titulo";s:10:"parrafo_h2";s:22:"<p>primer parrafo</p>\n";}s:6:"item-1";a:2:{s:9:"titulo_h2";s:14:"segundo titulo";s:10:"parrafo_h2";s:23:"<p>segundo parrafo</p>\n";}s:6:"item-2";a:2:{s:9:"titulo_h2";s:13:"tercer titulo";s:10:"parrafo_h2";s:22:"<p>tercer parrafo</p>\n";}s:6:"item-3";a:2:{s:9:"titulo_h2";s:13:"cuarto titulo";s:10:"parrafo_h2";s:22:"<p>cuarto parrafo</p>\n";}}'

print("\nProbando deserialización directa...")
try:
    result = phpserialize.loads(test_data.encode('utf-8'))
    print("Éxito! Resultado:", result)
except Exception as e:
    print("Error:", e)

# Prueba con comillas escapadas
test_data_escaped = test_data.replace('"', '\\"')
print("\nProbando con comillas escapadas...")
try:
    # Primero desescapar
    test_data_unescaped = test_data_escaped.replace('\\"', '"')
    result = phpserialize.loads(test_data_unescaped.encode('utf-8'))
    print("Éxito! Resultado:", result)
except Exception as e:
    print("Error:", e)
