import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

# ════════════════════════════════════════════════
# 📤 Subida de archivos JSON a Google Drive
# ════════════════════════════════════════════════

def subir_json_a_drive(nombre_archivo, contenido_bytes, carpeta_id=None):
    st.info("📤 Subiendo JSON a Google Drive (cuenta de servicio)...")

    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

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

        return archivo.get("webViewLink")

    except Exception as e:
        st.error(f"❌ Error al subir el archivo a Google Drive: {e}")
        return None

# ════════════════════════════════════════════════
# 📁 Obtener subcarpetas desde carpeta SERPY
# ════════════════════════════════════════════════

def obtener_proyectos_drive(folder_id_principal):
    try:
        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        resultados = service.files().list(
            q=f"'{folder_id_principal}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()

        carpetas = {f["name"]: f["id"] for f in resultados.get("files", [])}
        return carpetas

    except Exception as e:
        st.error(f"❌ Error al obtener subcarpetas: {e}")
        return {}

# ════════════════════════════════════════════════
# 📁 Crear nueva subcarpeta dentro de SERPY
# ════════════════════════════════════════════════

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
