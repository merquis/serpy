# image_processor.py
from PIL import Image
from io import BytesIO
import os

def process_image(input_path, output_path, size=(800, 600), quality=85):
    """
    Redimensiona y comprime una imagen.
    - input_path: ruta de la imagen original
    - output_path: ruta donde guardar la imagen procesada
    - size: tupla (ancho, alto) para redimensionar
    - quality: calidad de compresión JPEG
    """
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        img.thumbnail(size)
        img.save(output_path, "JPEG", quality=quality, optimize=True)

def get_hotel_folders(images_root):
    """
    Devuelve una lista de carpetas de hoteles (subdirectorios en images_root)
    """
    return [
        d for d in os.listdir(images_root)
        if os.path.isdir(os.path.join(images_root, d))
    ]

def get_images_for_hotel(images_root, hotel_folder):
    """
    Devuelve una lista de nombres de archivos de imagen para un hotel dado.
    """
    folder_path = os.path.join(images_root, hotel_folder)
    if not os.path.exists(folder_path):
        return []
    return [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    ]
