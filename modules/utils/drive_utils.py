# modules/utils/drive_utils.py
import streamlit as st
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ════════════════════════════════════════════════
# 🔐 Credenciales desde secrets
# ════════════════════════════════════════════════
def obtener_credenciales(scopes):
    try:
        json_keyfile_dict = dict(st.secrets["drive_service_account"])
        return service_account.Credentials.from_service_account_info(
            json_keyfile_dict, scopes=scopes
        )
    except Exception as e:
        st.error(f"❌ Error al obtener credenciales: {e}")
        return None

# ════════════════════════════════════════════════
# 📤 Subir JSON (atajo histórico)
# ════════════════════════════════════════════════
def subir_json_a_drive(nombre_archivo, contenido_bytes, carpeta_id=None):
    st.info("📤 Subiendo JSON a Google Drive…")
    return subir_archivo_a_drive(
        contenido=contenido_bytes,
        nombre_archivo=nombre_archivo,
        carpeta_id=carpeta_id,
        mime_type="application/json"
    )

# ════════════════════════════════════════════════
# 📤 Subir cualquier archivo (bytes o str)
# ════════════════════════════════════════════════
def subir_archivo_a_drive(contenido, nombre_archivo, carpeta_id=None,
                          mime_type="application/octet-stream"):
    """
    Sube un archivo a Google Drive (cuenta de servicio).
    - `contenido`  : bytes o str
    - `mime_type`  : tipo MIME (por defecto binario)
    Devuelve el enlace webViewLink o None si falla.
    """
    try:
        creds = obtener_credenciales(["https://www.googleapis.com/auth/drive"])
        if creds is None:
            return None

        service = build("drive", "v3", credentials=creds)

        # Asegurar bytes
        if isinstance(contenido, str):
            contenido = contenido.encode("utf-8")

        media = MediaIoBaseUpload(io.BytesIO(contenido), mimetype=mime_type)
        metadata = {"name": nombre_archivo, "mimeType": mime_type}
        if carpeta_id:
            metadata["parents"] = [carpeta_id]

        archivo = service.files().create(
            body=metadata, media_body=media, fields="id, webViewLink"
        ).execute()

        return archivo.get("webViewLink")
    except Exception as e:
        st.error(f"❌ Error al subir archivo a Drive: {e}")
        return None

# ════════════════════════════════════════════════
# 📁 Listar proyectos (subcarpetas)
# ════════════════════════════════════════════════
def obtener_proyectos_drive(folder_id_principal):
    try:
        creds = obtener_credenciales(["https://www.googleapis.com/auth/drive"])
        if creds is None:
            return {}
        service = build("drive", "v3", credentials=creds)
        res = service.files().list(
            q=f"'{folder_id_principal}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        return {f["name"]: f["id"] for f in res.get("files", [])}
    except Exception as e:
        st.error(f"❌ Error al obtener carpetas: {e}")
        return {}

# ════════════════════════════════════════════════
# 📁 Crear subcarpeta
# ════════════════════════════════════════════════
def crear_carpeta_en_drive(nombre_carpeta, parent_id):
    try:
        creds = obtener_credenciales(["https://www.googleapis.com/auth/drive"])
        if creds is None:
            return None
        service = build("drive", "v3", credentials=creds)
        metadata = {
            "name": nombre_carpeta,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]
        }
        nueva = service.files().create(body=metadata, fields="id").execute()
        return nueva.get("id")
    except Exception as e:
        st.error(f"❌ Error al crear carpeta: {e}")
        return None

# ════════════════════════════════════════════════
# 📄 Listar JSON dentro de carpeta
# ════════════════════════════════════════════════
def listar_archivos_en_carpeta(folder_id):
    try:
        creds = obtener_credenciales(["https://www.googleapis.com/auth/drive"])
        if creds is None:
            return {}
        service = build("drive", "v3", credentials=creds)
        res = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/json' and trashed=false",
            fields="files(id, name)"
        ).execute()
        return {f["name"]: f["id"] for f in res.get("files", [])}
    except Exception as e:
        st.error(f"❌ Error al listar archivos: {e}")
        return {}

# ════════════════════════════════════════════════
# 📥 Obtener contenido de archivo (bytes)
# ════════════════════════════════════════════════
def obtener_contenido_archivo_drive(file_id):
    try:
        creds = obtener_credenciales(["https://www.googleapis.com/auth/drive.readonly"])
        if creds is None:
            return None
        service = build("drive", "v3", credentials=creds)
        return service.files().get_media(fileId=file_id).execute()
    except Exception as e:
        st.error(f"❌ Error al obtener contenido: {e}")
        return None
