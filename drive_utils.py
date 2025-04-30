import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

def subir_json_a_drive(nombre_archivo, contenido_bytes):
    # Guardar archivo temporal
    with open(nombre_archivo, 'wb') as f:
        f.write(contenido_bytes)

    # Autenticación con client_secrets.json
    gauth = GoogleAuth()
    gauth.LoadClientConfigFile("client_secrets.json")
    gauth.CommandLineAuth()  # Modo consola, compatible con servidores
    drive = GoogleDrive(gauth)

    # Crear y subir archivo
    file_drive = drive.CreateFile({'title': nombre_archivo})
    file_drive.SetContentFile(nombre_archivo)
    file_drive.Upload()

    os.remove(nombre_archivo)  # Limpiar archivo local
    return file_drive['alternateLink']
