import json
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseUpload
import io

# Función para subir archivos JSON a Google Drive
def subir_json_a_drive(nombre_archivo, contenido_bytes, carpeta_id=None):
    st.info("📤 Subiendo JSON a Google Drive (cuenta de servicio)...")

    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        media = MediaIoBaseUpload(io.BytesIO(contenido_bytes), mimetype="application/json")
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

        return archivo.get("webViewLink")

    except Exception as e:
        st.error(f"❌ Error al subir el archivo a Google Drive: {e}")
        return None


# Función para obtener las subcarpetas de una carpeta principal
def obtener_proyectos_drive(folder_id_principal):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        # Consulta para obtener las subcarpetas de una carpeta específica
        resultados = service.files().list(
            q=f"'{folder_id_principal}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()

        carpetas = {f["name"]: f["id"] for f in resultados.get("files", [])}
        return carpetas

    except Exception as e:
        st.error(f"❌ Error al obtener subcarpetas: {e}")
        return {}


# Función para crear una nueva carpeta dentro de la carpeta principal
def crear_carpeta_en_drive(nombre_carpeta, parent_id):
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
            fields="id, name"
        ).execute()

        return nueva_carpeta.get("id")

    except Exception as e:
        st.error(f"❌ Error al crear la carpeta: {e}")
        return None


# Función para listar los archivos dentro de una carpeta en Google Drive
def listar_archivos_en_carpeta(folder_id):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        # Consulta para listar los archivos JSON dentro de una carpeta específica
        resultados = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/json' and trashed=false",
            fields="files(id, name)"
        ).execute()

        archivos = {f["name"]: f["id"] for f in resultados.get("files", [])}
        return archivos

    except Exception as e:
        st.error(f"❌ Error al obtener archivos: {e}")
        return {}


# Función para obtener el contenido de un archivo JSON desde Google Drive por ID
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
        return None
