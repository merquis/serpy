def subir_json_a_drive(nombre_archivo, data_json, carpeta_id):
    import json
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmpfile:
        json.dump(data_json, tmpfile, ensure_ascii=False, indent=2)
        tmpfile.flush()

        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        drive = GoogleDrive(gauth)

        file_drive = drive.CreateFile({
            "title": nombre_archivo,
            "parents": [{"id": carpeta_id}]
        })
        file_drive.SetContentFile(tmpfile.name)
        file_drive.Upload()
