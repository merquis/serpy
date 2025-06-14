from google import genai
import json

# Imprimir los atributos disponibles
print("Atributos de genai:")
print(dir(genai))
print("\n")

# Ver si tiene types
if hasattr(genai, 'types'):
    print("Atributos de genai.types:")
    print(dir(genai.types))
    print("\n")

# Ver si tiene Client
if hasattr(genai, 'Client'):
    print("genai.Client existe")
    print("Métodos de Client:")
    # No podemos instanciar sin API key, pero podemos ver la clase
    print(dir(genai.Client))
