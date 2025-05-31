from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from services.image_processor import (
    get_hotel_folders,
    get_images_for_hotel,
    process_image,
)
import os
import shutil

IMAGES_ROOT = "/shared/images"

app = FastAPI(
    title="Hotel Image Service",
    description="Microservicio para servir y procesar imágenes de hoteles",
    version="1.0.0"
)

# Montar imágenes como archivos estáticos para acceso directo
app.mount("/images", StaticFiles(directory=IMAGES_ROOT), name="images")

@app.get("/api/hotels")
def list_hotels():
    """
    Devuelve la lista de carpetas de hoteles.
    """
    if not os.path.exists(IMAGES_ROOT):
        return JSONResponse(content=[])
    hotels = get_hotel_folders(IMAGES_ROOT)
    return JSONResponse(content=hotels)

@app.get("/api/hotels/{hotel}/images")
def list_images_for_hotel(hotel: str):
    """
    Devuelve la lista de imágenes para un hotel.
    """
    images = get_images_for_hotel(IMAGES_ROOT, hotel)
    return JSONResponse(content=images)

@app.post("/api/hotels/{hotel}/images/upload")
async def upload_and_process_image(
    hotel: str,
    file: UploadFile = File(...)
):
    """
    Sube y procesa una imagen para un hotel (redimensiona y comprime).
    """
    hotel_folder = os.path.join(IMAGES_ROOT, hotel)
    os.makedirs(hotel_folder, exist_ok=True)
    temp_path = os.path.join(hotel_folder, "temp_" + file.filename)
    final_path = os.path.join(hotel_folder, file.filename)
    # Guardar archivo temporalmente
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # Procesar imagen (redimensionar y comprimir)
    try:
        process_image(temp_path, final_path)
        os.remove(temp_path)
    except Exception as e:
        os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error procesando imagen: {e}")
    return {"filename": file.filename, "hotel": hotel}

# Endpoint para servir imágenes individuales (opcional, ya que StaticFiles lo hace)
@app.get("/images/{hotel_folder}/{filename}")
def serve_image(hotel_folder: str, filename: str):
    """
    Sirve una imagen concreta de un hotel.
    """
    image_path = os.path.join(IMAGES_ROOT, hotel_folder, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(image_path, media_type="image/jpeg")
