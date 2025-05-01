import os
import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

def subir_json_a_drive(nombre_archivo, contenido_bytes):
    st.info("📤 Subiendo JSON a Google Drive (cuenta de servicio)...")

    try:
        # Cargar credenciales desde archivo
        ruta_credenciales = os.path.join(os.path.dirname(__file__), "drive_service_account.json")
        creds = service_account.Credentials.from_service_account_file(
            ruta_credenciales,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        # Crear cliente Drive
        service = build("drive", "v3", credentials=creds)

        # ID de carpeta (SERPY) → dejar en blanco si quieres raíz
        carpeta_id = None  # Si ya sabes el ID de la carpeta SERPY, ponlo aquí como string

        # Subir archivo como JSON
        media = MediaInMemoryUpload(contenido_bytes, mimetype="application/json")
        file_metadata = {
            "name": nombre_archivo,
            "mimeType": "application/json"
        }
        if carpeta_id:
            file_metadata["parents"] = [carpeta_id]

        archivo = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        enlace = archivo.get("webViewLink")
        return enlace

    except Exception as e:
        st.error(f"❌ Error al subir el archivo a Google Drive: {e}")
        return None
