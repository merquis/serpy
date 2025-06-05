#!/usr/bin/env python3
import requests
import json

print("🔍 Probando servicio de imágenes\n")

# URL base
base_url = "https://images.videocursosweb.com"

# 1. Probar health
print("1. Probando endpoint de salud...")
try:
    response = requests.get(f"{base_url}/api/v1/health", timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    else:
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

print("\n2. Probando con diferentes API keys...")
api_keys = [
    "serpy-demo-key-2025",
    "secure-api-key-here",
    "tu-api-key-segura-aqui"
]

valid_key = None
for key in api_keys:
    try:
        print(f"   Probando: {key}")
        headers = {"X-API-Key": key}
        response = requests.get(f"{base_url}/api/v1/jobs?limit=1", headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ API key válida!")
            valid_key = key
            break
        elif response.status_code == 403:
            print(f"   ❌ API key inválida")
        else:
            print(f"   Response: {response.text[:100]}...")
    except Exception as e:
        print(f"   Error: {e}")

if valid_key:
    print(f"\n✅ API Key válida encontrada: {valid_key}")
    print("\n3. Comando para descargar imágenes:")
    print(f'curl -X POST "{base_url}/api/v1/download/from-api-url" \\')
    print(f'  -H "X-API-Key: {valid_key}" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"api_url":"https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b","collection_name":"hotel-booking"}\'')
    
    print("\n4. Comando en una línea:")
    print(f'curl -X POST "{base_url}/api/v1/download/from-api-url?api_url=https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b&collection_name=hotel-booking" -H "X-API-Key: {valid_key}"')
else:
    print("\n❌ No se encontró una API key válida")
    print("\nPosibles problemas:")
    print("1. El servicio no está respondiendo correctamente")
    print("2. La API key configurada en el servidor es diferente")
    print("3. Hay un problema de conectividad")
