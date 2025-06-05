"""
Ejemplo de uso del microservicio de imágenes para descargar fotos de hoteles
"""
import requests
import json
import time

# Configuración
API_BASE_URL = "http://localhost:8003/api/v1"  # Cambiar por tu URL en producción
API_KEY = "tu-api-key-aqui"  # Cambiar por tu API key real

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def check_health():
    """Verifica que el servicio esté funcionando"""
    response = requests.get(f"{API_BASE_URL}/health")
    if response.status_code == 200:
        print("✅ Servicio funcionando correctamente")
        return True
    else:
        print("❌ Error: El servicio no está disponible")
        return False


def download_hotel_images(document_id):
    """Descarga las imágenes de un hotel específico"""
    print(f"\n📥 Descargando imágenes del hotel {document_id}...")
    
    response = requests.post(
        f"{API_BASE_URL}/download/document/serpy_db/hotel-booking/{document_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        job = response.json()
        print(f"✅ Job creado: {job['id']}")
        return job['id']
    else:
        print(f"❌ Error: {response.text}")
        return None


def download_all_hotels():
    """Descarga las imágenes de TODOS los hoteles (usar con cuidado)"""
    print("\n📥 Descargando imágenes de TODA la colección hotel-booking...")
    
    response = requests.post(
        f"{API_BASE_URL}/download/collection/serpy_db/hotel-booking",
        headers=headers
    )
    
    if response.status_code == 200:
        job = response.json()
        print(f"✅ Job creado: {job['id']}")
        print(f"📊 Total de documentos a procesar: {job.get('metadata', {}).get('total_documents', 'desconocido')}")
        return job['id']
    else:
        print(f"❌ Error: {response.text}")
        return None


def download_hotels_with_filter(filter_query, limit=10):
    """Descarga imágenes de hoteles que cumplan ciertos criterios"""
    print(f"\n📥 Descargando imágenes con filtro: {filter_query}")
    
    data = {
        "database": "serpy_db",
        "collection": "hotel-booking",
        "filter": filter_query,
        "limit": limit
    }
    
    response = requests.post(
        f"{API_BASE_URL}/download/batch",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        job = response.json()
        print(f"✅ Job creado: {job['id']}")
        return job['id']
    else:
        print(f"❌ Error: {response.text}")
        return None


def check_job_status(job_id):
    """Verifica el estado de un job"""
    response = requests.get(
        f"{API_BASE_URL}/jobs/{job_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        job = response.json()
        print(f"\n📊 Estado del Job {job_id}:")
        print(f"  - Estado: {job['status']}")
        print(f"  - Progreso: {job['processed_items']}/{job['total_items']} ({job['progress_percentage']:.1f}%)")
        print(f"  - Items fallidos: {job['failed_items']}")
        
        if job['status'] == 'completed':
            print(f"  - Duración: {job['duration']:.2f} segundos")
        
        return job
    else:
        print(f"❌ Error obteniendo estado del job: {response.text}")
        return None


def wait_for_job(job_id, check_interval=5):
    """Espera a que un job termine"""
    print(f"\n⏳ Esperando a que termine el job {job_id}...")
    
    while True:
        job = check_job_status(job_id)
        if not job:
            break
            
        if job['status'] in ['completed', 'failed', 'cancelled']:
            print(f"\n✅ Job terminado con estado: {job['status']}")
            break
            
        time.sleep(check_interval)


def get_hotel_ids_from_api():
    """Obtiene los IDs de los hoteles desde la API pública"""
    print("\n🔍 Obteniendo lista de hoteles desde la API...")
    
    response = requests.get("https://api.serpsrewrite.com/hotel-booking")
    if response.status_code == 200:
        data = response.json()
        hotels = data.get('documents', [])
        print(f"✅ Encontrados {len(hotels)} hoteles")
        
        # Mostrar algunos ejemplos
        for i, hotel in enumerate(hotels[:3]):
            print(f"\n  Hotel {i+1}:")
            print(f"    - ID: {hotel['_id']}")
            print(f"    - Nombre: {hotel.get('nombre_alojamiento', 'Sin nombre')}")
            print(f"    - Ciudad: {hotel.get('ciudad', 'Sin ciudad')}")
            print(f"    - Imágenes: {len(hotel.get('imagenes', []))} fotos")
        
        return [hotel['_id'] for hotel in hotels]
    else:
        print("❌ Error obteniendo hoteles de la API")
        return []


# EJEMPLOS DE USO
if __name__ == "__main__":
    print("=== EJEMPLOS DE DESCARGA DE IMÁGENES DE HOTELES ===")
    
    # 1. Verificar que el servicio funciona
    if not check_health():
        print("⚠️  Asegúrate de que el servicio esté ejecutándose")
        exit(1)
    
    # 2. Obtener IDs de hoteles desde la API
    hotel_ids = get_hotel_ids_from_api()
    
    if hotel_ids:
        # 3. Descargar imágenes del primer hotel
        print("\n--- EJEMPLO 1: Descargar un hotel específico ---")
        job_id = download_hotel_images(hotel_ids[0])
        if job_id:
            wait_for_job(job_id)
    
    # 4. Descargar hoteles con alta valoración
    print("\n--- EJEMPLO 2: Descargar hoteles con valoración >= 9 ---")
    job_id = download_hotels_with_filter(
        filter_query={"valoracion_global": {"$gte": 9}},
        limit=5
    )
    if job_id:
        wait_for_job(job_id)
    
    # 5. Descargar hoteles de una ciudad específica
    print("\n--- EJEMPLO 3: Descargar hoteles de una ciudad ---")
    job_id = download_hotels_with_filter(
        filter_query={"ciudad": {"$regex": "Madrid", "$options": "i"}},
        limit=3
    )
    if job_id:
        wait_for_job(job_id)
    
    # NOTA: Para descargar TODOS los hoteles (¡cuidado!):
    # job_id = download_all_hotels()
    # if job_id:
    #     wait_for_job(job_id)
    
    print("\n✅ Ejemplos completados!")
    print("\n📁 Las imágenes se guardan en: /images/serpy_db/hotel-booking/[id]-[nombre]/")
