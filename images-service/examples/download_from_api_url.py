"""
Ejemplo simple: Descargar imágenes desde una URL de API externa
"""
import requests
import time

# Configuración
IMAGES_SERVICE_URL = "http://localhost:8003/api/v1"
API_KEY = "tu-api-key-aqui"

def download_images_from_api_url(api_url):
    """
    Descarga todas las imágenes de los documentos en una URL de API
    
    Args:
        api_url: URL de la API que contiene los documentos con imágenes
    """
    print(f"\n🌐 Descargando imágenes desde: {api_url}")
    
    # Hacer la petición al microservicio
    response = requests.post(
        f"{IMAGES_SERVICE_URL}/download/from-api-url",
        headers={"X-API-Key": API_KEY},
        params={"api_url": api_url}
    )
    
    if response.status_code == 200:
        job = response.json()
        print(f"✅ Job creado exitosamente!")
        print(f"   - ID: {job['id']}")
        print(f"   - Total documentos: {job['metadata']['total_documents']}")
        
        # Monitorear el progreso
        monitor_job(job['id'])
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")


def monitor_job(job_id):
    """Monitorea el progreso de un job hasta que termine"""
    print(f"\n⏳ Monitoreando job {job_id}...")
    
    while True:
        response = requests.get(
            f"{IMAGES_SERVICE_URL}/jobs/{job_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            job = response.json()
            
            # Mostrar progreso
            print(f"\r📊 Progreso: {job['processed_items']}/{job['total_items']} " +
                  f"({job['progress_percentage']:.1f}%) - Estado: {job['status']}", end="")
            
            # Verificar si terminó
            if job['status'] in ['completed', 'failed', 'cancelled']:
                print()  # Nueva línea
                
                if job['status'] == 'completed':
                    print(f"\n✅ ¡Descarga completada!")
                    print(f"   - Documentos procesados: {job['processed_items']}")
                    print(f"   - Items fallidos: {job['failed_items']}")
                    print(f"   - Duración: {job['duration']:.2f} segundos")
                else:
                    print(f"\n❌ Job terminado con estado: {job['status']}")
                    if job['errors']:
                        print("   Errores:")
                        for error in job['errors']:
                            print(f"   - {error['message']}")
                break
        else:
            print(f"\n❌ Error obteniendo estado del job: {response.text}")
            break
        
        time.sleep(3)  # Esperar 3 segundos antes de verificar de nuevo


# EJEMPLOS DE USO
if __name__ == "__main__":
    print("=== DESCARGA DE IMÁGENES DESDE API EXTERNA ===")
    
    # Ejemplo 1: Descargar imágenes de hoteles desde tu API
    print("\n--- EJEMPLO 1: API de Hoteles ---")
    download_images_from_api_url("https://api.videocursosweb.com/hotel-booking")
    
    # Ejemplo 2: Puedes usar cualquier API que devuelva documentos con imágenes
    # print("\n--- EJEMPLO 2: Otra API ---")
    # download_images_from_api_url("https://otra-api.com/productos")
    
    print("\n📁 Las imágenes se guardan en: /images/serpy_db/temp_[collection]_[id]/")
    print("   Cada hotel tendrá su carpeta: [document_id]-[nombre_hotel]/")
