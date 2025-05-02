import os
import streamlit as st
from pydrive2.auth import ServiceAccountCredentials
from pydrive2.drive import GoogleDrive

def subir_json_a_drive(nombre_archivo, contenido_bytes):
    st.write("🚀 Subiendo JSON a Google Drive con cuenta de servicio...")

    # Guardar archivo temporal
    with open(nombre_archivo, 'wb') as f:
        f.write(contenido_bytes)

    try:
        # Autenticación con cuenta de servicio
        gauth = ServiceAccountCredentials()
        gauth.LoadServiceConfigFile("credentials.json")  # este es tu archivo de cuenta de servicio
        gauth.Authorize()
        drive = GoogleDrive(gauth)

        # Crear y subir archivo
        file_drive = drive.CreateFile({'title': nombre_archivo})
        file_drive.SetContentFile(nombre_archivo)
        file_drive.Upload()

        os.remove(nombre_archivo)
        return file_drive['alternateLink']
    except Exception as e:
        st.error(f"❌ Error subiendo a Google Drive: {e}")
        return None
