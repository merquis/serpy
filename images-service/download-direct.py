#!/usr/bin/env python3
"""
Script para descargar imágenes directamente desde la API sin usar MongoDB
"""
import os
import httpx
import asyncio
from pathlib import Path
import json
from datetime import datetime

async def download_image(session, url, save_path):
    """Descarga una imagen"""
    try:
        response = await session.get(url, timeout=30.0)
        response.raise_for_status()
        
        # Guardar imagen
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        
        print(f"✅ Descargada: {save_path.name}")
        return True
    except Exception as e:
        print(f"❌ Error descargando {url}: {e}")
        return False

async def download_from_api(api_url, output_dir="/var/www/images"):
    """Descarga imágenes desde la API"""
    print(f"🔍 Obteniendo datos de: {api_url}")
    
    # Obtener datos de la API
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url)
        response.raise_for_status()
        data = response.json()
    
    # Extraer documento
    if isinstance(data, dict):
        documents = [data]
    elif isinstance(data, list):
        documents = data
    else:
        print("❌ Formato de datos no reconocido")
        return
    
    print(f"📋 Encontrados {len(documents)} documentos")
    
    # Procesar cada documento
    total_images = 0
    downloaded = 0
    
    async with httpx.AsyncClient() as session:
        for doc in documents:
            # Extraer ID y nombre
            doc_id = doc.get('_id', doc.get('id', 'unknown'))
            nombre = doc.get('nombre_alojamiento', doc.get('titulo_h1', 'sin-nombre'))
            
            # Sanitizar nombre para directorio
            nombre_safe = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).rstrip()
            nombre_safe = nombre_safe.replace(' ', '-').lower()[:50]
            
            # Crear directorio
            doc_dir = Path(output_dir) / "serpy_db" / "hotel-booking" / f"{doc_id}-{nombre_safe}" / "original"
            doc_dir.mkdir(parents=True, exist_ok=True)
            
            print(f"\n📁 Procesando: {nombre}")
            print(f"   ID: {doc_id}")
            
            # Buscar imágenes en el documento
            imagenes = doc.get('imagenes', [])
            if not imagenes:
                # Buscar en otros campos posibles
                for field in ['images', 'fotos', 'photos', 'galeria']:
                    if field in doc and isinstance(doc[field], list):
                        imagenes = doc[field]
                        break
            
            if not imagenes:
                print("   ⚠️  No se encontraron imágenes")
                continue
            
            print(f"   📷 {len(imagenes)} imágenes encontradas")
            total_images += len(imagenes)
            
            # Descargar imágenes
            tasks = []
            for i, img_url in enumerate(imagenes):
                if isinstance(img_url, str) and img_url.startswith('http'):
                    # Determinar extensión
                    ext = '.jpg'
                    if '.png' in img_url.lower():
                        ext = '.png'
                    elif '.webp' in img_url.lower():
                        ext = '.webp'
                    
                    save_path = doc_dir / f"img_{i+1:03d}{ext}"
                    tasks.append(download_image(session, img_url, save_path))
            
            # Ejecutar descargas en paralelo
            if tasks:
                results = await asyncio.gather(*tasks)
                downloaded += sum(results)
            
            # Guardar metadata
            metadata = {
                "document_id": str(doc_id),
                "nombre": nombre,
                "total_images": len(imagenes),
                "downloaded": sum(results) if tasks else 0,
                "timestamp": datetime.now().isoformat(),
                "source_url": api_url
            }
            
            metadata_path = doc_dir.parent / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    print(f"\n✅ Descarga completada!")
    print(f"   Total imágenes: {total_images}")
    print(f"   Descargadas: {downloaded}")
    print(f"   Guardadas en: {output_dir}/serpy_db/hotel-booking/")

async def main():
    # URL de la API
    api_url = "https://api.videocursosweb.com/hotel-booking/6840bc4e949575a0325d921b"
    
    # Directorio de salida (cambiar según necesites)
    output_dir = "/var/www/images"  # Para VPS
    # output_dir = "./images"  # Para pruebas locales
    
    await download_from_api(api_url, output_dir)

if __name__ == "__main__":
    asyncio.run(main())
