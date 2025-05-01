import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import streamlit as st

# Obtener credenciales
def _get_drive_service():
    json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        json_keyfile_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

# Listar archivos JSON en carpeta
def listar_archivos_en_carpeta(carpeta_id):
    try:
        service = _get_drive_service()
        query = f"'{carpeta_id}' in parents and mimeType='application/json' and trashed=false"
        archivos = service.files().list(q=query, fields="files(id, name)").execute()
        return {archivo["name"]: archivo["id"] for archivo in archivos.get("files", [])}
    except Exception as e:
        st.error(f"❌ Error al listar archivos: {e}")
        return {}

# Obtener contenido del archivo por ID
def obtener_contenido_archivo_drive(file_id):
    try:
        service = _get_drive_service()
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read()  # Bytes (igual que archivo_subido.read())
    except Exception as e:
        st.error(f"❌ Error al obtener archivo desde Drive: {e}")
        return None
