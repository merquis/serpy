import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

def subir_json_a_drive(nombre_archivo, contenido_bytes, carpeta_id=None):
    st.info("📤 Subiendo JSON a Google Drive (cuenta de servicio)...")

    try:
        # Leer las credenciales desde st.secrets
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        # Crear cliente Drive
        service = build("drive", "v3", credentials=creds)

        # Preparar archivo
        media = MediaInMemoryUpload(contenido_bytes, mimetype="application/json")
        file_metadata = {
            "name": nombre_archivo,
            "mimeType": "application/json"
        }
        if carpeta_id:
            file_metadata["parents"] = [carpeta_id]

        # Subir archivo
        archivo = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()

        return archivo.get("webViewLink")

    except Exception as e:
        st.error(f"❌ Error al subir el archivo a Google Drive: {e}")
        return None
