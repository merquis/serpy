import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Subir archivos JSON a Google Drive
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


# Obtener subcarpetas de una carpeta específica
def obtener_proyectos_drive(folder_id_principal):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        # Verificación adicional para asegurarse de que el folder_id_principal no esté vacío
        if not folder_id_principal:
            st.error("❌ El ID de la carpeta principal no está definido.")
            return {}

        # Consulta para obtener las subcarpetas
        query = f"'{folder_id_principal}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()

        if not results.get("files"):
            st.error("❌ No se encontraron subcarpetas en la carpeta especificada.")
            return {}

        carpetas = {f["name"]: f["id"] for f in results.get("files", [])}
        return carpetas

    except HttpError as error:
        st.error(f"❌ Error al obtener las subcarpetas: {error}")
        return {}


# Función para crear subcarpetas
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


# Listar archivos JSON dentro de una carpeta
def listar_archivos_en_carpeta(folder_id):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        # Verificación de que el folder_id no esté vacío
        if not folder_id:
            st.error("❌ El ID de la carpeta es inválido.")
            return {}

        query = f"'{folder_id}' in parents and mimeType='application/json' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()

        archivos = {f["name"]: f["id"] for f in results.get("files", [])}
        return archivos

    except HttpError as error:
        st.error(f"❌ Error al obtener archivos: {error}")
        return {}


# Obtener el contenido de un archivo JSON desde Google Drive
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
