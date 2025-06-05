#!/usr/bin/env python3
"""
Script para probar la conexión a MongoDB desde dentro y fuera de Docker
"""
import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Probar diferentes URIs de conexión
test_uris = [
    ("Host Docker Internal", "mongodb://host.docker.internal:27017"),
    ("Localhost", "mongodb://localhost:27017"),
    ("IP Docker Bridge", "mongodb://172.17.0.1:27017"),
    ("Desde .env", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
]

print("🔍 Probando conexiones a MongoDB...\n")

for name, uri in test_uris:
    try:
        print(f"Probando: {name}")
        print(f"URI: {uri}")
        
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Forzar conexión
        client.admin.command('ping')
        
        print("✅ Conexión exitosa!")
        print(f"   Versión: {client.server_info()['version']}")
        print(f"   Bases de datos: {client.list_database_names()[:3]}...")
        
        # Si encontramos una conexión exitosa, actualizar recomendación
        print(f"\n📌 USA ESTA URI EN TU .env:")
        print(f"   MONGODB_URI={uri}")
        break
        
    except ConnectionFailure as e:
        print(f"❌ Fallo: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
    
    print("-" * 50)
else:
    print("\n❌ No se pudo conectar a MongoDB con ninguna URI")
    print("\n💡 Sugerencias:")
    print("1. Verifica que MongoDB esté ejecutándose:")
    print("   sudo systemctl status mongod")
    print("2. Verifica que MongoDB escuche en todas las interfaces:")
    print("   sudo netstat -tlnp | grep 27017")
    print("3. Si solo escucha en 127.0.0.1, edita /etc/mongod.conf:")
    print("   bindIp: 0.0.0.0")
