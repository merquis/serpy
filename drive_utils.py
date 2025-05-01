import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import streamlit as st

def subir_json_a_drive(nombre_archivo, contenido_bytes):
    st.write("🚀 Función subir_json_a_drive llamada.")

    # Guardar archivo temporal
    with open(nombre_archivo, 'wb') as f:
        f.write(contenido_bytes)

    # Simulación de autenticación (comentar esta parte para debug)
    try:
        gauth = GoogleAuth()
        gauth.LoadClientConfigFile("client_secrets.json")
        st.info("🧪 Ejecutando CommandLineAuth...")
        gauth.LocalWebserverAuth()
        drive = GoogleDrive(gauth)

        # Crear y subir archivo
        file_drive = drive.CreateFile({'title': nombre_archivo})
        file_drive.SetContentFile(nombre_archivo)
        file_drive.Upload()

        os.remove(nombre_archivo)
        return file_drive['alternateLink']
    except Exception as e:
        st.error(f"❌ Error en la autenticación o subida: {e}")
        return None
