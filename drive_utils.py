import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

def subir_json_a_drive(nombre_archivo, contenido_bytes, carpeta_id=None):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds)

        media = MediaIoBaseUpload(io.BytesIO(contenido_bytes), mimetype="application/json")
        metadata = {"name": nombre_archivo}
        if carpeta_id:
            metadata["parents"] = [carpeta_id]

        archivo = service.files().create(
            body=metadata,
            media_body=media,
            fields="webViewLink"
        ).execute()

        return archivo.get("webViewLink")
    except Exception as e:
        st.error(f"❌ Error al subir a Drive: {e}")
        return None
