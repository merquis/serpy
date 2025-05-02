import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ════════════════════════════════════════════════
# 📁 Obtener subcarpetas desde carpeta SERPY
# ════════════════════════════════════════════════
def obtener_proyectos_drive(folder_id_principal):
    try:
        # Imprime el ID de la carpeta para asegurarnos que es correcto
        st.write(f"Folder ID: {folder_id_principal}")

        json_keyfile_dict = json.loads(st.secrets["drive_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            json_keyfile_dict,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build("drive", "v3", credentials=creds)

        # Simplificando la consulta temporalmente para verificar que funciona
        resultados = service.files().list(
            q=f"'{folder_id_principal}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()

        # Verificar los resultados obtenidos
        st.write(f"Archivos encontrados: {resultados.get('files', [])}")

        # Si encontramos carpetas, las devolvemos
        carpetas = {f["name"]: f["id"] for f in resultados.get("files", [])}
        return carpetas

    except Exception as e:
        st.error(f"❌ Error al obtener subcarpetas: {e}")
        return {}

