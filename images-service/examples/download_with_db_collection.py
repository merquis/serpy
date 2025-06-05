#!/usr/bin/env python3
"""
Ejemplo de cómo usar el endpoint de descarga con database y collection dinámicos
"""
import httpx
import asyncio
import json

async def download_hotel_images():
    """Ejemplo de descarga de imágenes con database y collection específicos"""
    
    # Configuración
    url = "https://images.serpsrewrite.com/api/v1/download/from-api-url-simple"
    api_key = "serpy-demo-key-2025"
    
    # ID del hotel en MongoDB
    mongo_id = "6840bc4e949575a0325d921b"
    
    # Información de la base de datos y colección
    database_name = "serpy_db"  # Este viene de st.secrets["mongodb"]["db"]
    collection_name = "hotel-booking"  # Este es el nombre de la colección donde se guardó
    
    # Construir el body del request
    json_data = {
        "api_url": f"https://api.serpsrewrite.com/{collection_name}/{mongo_id}",
        "database_name": database_name,
        "collection_name": collection_name
    }
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    print(f"📤 Enviando petición de descarga...")
    print(f"   Database: {database_name}")
    print(f"   Collection: {collection_name}")
    print(f"   Document ID: {mongo_id}")
    print(f"\n📋 JSON Body:")
    print(json.dumps(json_data, indent=2))
    
    # Comando curl equivalente
    curl_cmd = f'''curl -X POST "{url}" \\
    -H "X-API-Key: {api_key}" \\
    -H "Content-Type: application/json" \\
    -d '{json.dumps(json_data)}'
    '''
    print(f"\n🔧 Comando CURL equivalente:")
    print(curl_cmd)
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                url,
                json=json_data,
                headers=headers
            )
            
            print(f"\n📥 Respuesta recibida:")
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Descarga iniciada exitosamente!")
                print(f"   Job ID: {result.get('id')}")
                print(f"   Documentos procesados: {result.get('documents_processed')}")
                print(f"   Total imágenes: {result.get('total_images')}")
                print(f"   Imágenes descargadas: {result.get('images_downloaded')}")
                print(f"   Ruta de almacenamiento: {result.get('storage_path')}")
                
                # La estructura de directorios será:
                # /images/serpy_db/hotel-booking/[mongo_id]-[hotel_name]/original/
                print(f"\n📁 Las imágenes se guardarán en:")
                print(f"   {result.get('storage_path')}/[mongo_id]-[hotel_name]/original/")
                
                # Y las URLs serán:
                print(f"\n🌐 URLs de las imágenes:")
                print(f"   https://images.serpsrewrite.com/api/v1/images/{database_name}/{collection_name}/[mongo_id]-[hotel_name]/original/img_001.jpg")
                
            else:
                print(f"\n❌ Error en la descarga:")
                print(response.text)
                
    except Exception as e:
        print(f"\n❌ Error al ejecutar la petición: {str(e)}")

async def main():
    """Función principal"""
    print("🏨 Ejemplo de descarga de imágenes con database y collection dinámicos")
    print("=" * 70)
    
    await download_hotel_images()

if __name__ == "__main__":
    asyncio.run(main())
