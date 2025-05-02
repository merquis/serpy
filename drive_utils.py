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

def listar_archivos_en_carpeta(folder_id):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds)
        resultados = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/json' and trashed=false",
            fields="files(id, name)"
        ).execute()
        return {f["name"]: f["id"] for f in resultados.get("files", [])}
    except Exception as e:
        st.error(f"❌ Error al listar archivos en Drive: {e}")
        return {}

def obtener_contenido_archivo_drive(file_id):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        service = build("drive", "v3", credentials=creds)
        contenido = service.files().get_media(fileId=file_id).execute()
        return contenido
    except Exception as e:
        st.error(f"❌ Error al obtener contenido del archivo: {e}")
        return Nonedef crear_carpeta_en_drive(nombre_carpeta, parent_id):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        folder_metadata = {
            "name": nombre_carpeta,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]
        }

        nueva_carpeta = service.files().create(
            body=folder_metadata,
            fields="id"
        ).execute()

        return nueva_carpeta.get("id")

    except Exception as e:
        st.error(f"❌ Error al crear carpeta en Drive: {e}")
        return None