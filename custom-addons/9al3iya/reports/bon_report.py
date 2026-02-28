import os
import mimetypes
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# ------------------------------------------------------------
# ⚙️ Configuration
# ------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/drive"]

# Chemin monté dans Docker (volume)
SERVICE_ACCOUNT_PATH = "/srv/google_credentials/service_account.json"

# ID du dossier racine Drive "Bon"
ROOT_FOLDER_ID = "1YVjJOOPHsVwW7TeE6oxQFSna9bEOylXa"


# ------------------------------------------------------------
# 🔐 Authentification (Service Account)
# ------------------------------------------------------------
def get_drive_servicev2():
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(
            f"Service account file not found at {SERVICE_ACCOUNT_PATH}"
        )

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH,
        scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


# ------------------------------------------------------------
# 📁 Dossiers
# ------------------------------------------------------------
def get_or_create_folderv2(service, parent_id, folder_name):
    results = service.files().list(
        q=(
            f"'{parent_id}' in parents and "
            f"name='{folder_name}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"trashed=false"
        ),
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]

    folder = service.files().create(
        body={
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id",
        supportsAllDrives=True,
    ).execute()

    return folder["id"]


# ------------------------------------------------------------
# ☁️ Upload
# ------------------------------------------------------------
def upload_to_drivev2(file_path, file_name, ste_name=None):
    service = get_drive_servicev2()

    parent_folder_id = ROOT_FOLDER_ID
    if ste_name:
        parent_folder_id = get_or_create_folderv2(service, ROOT_FOLDER_ID, ste_name)

    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/pdf"

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    uploaded = service.files().create(
        body={
            "name": file_name,
            "parents": [parent_folder_id],
        },
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True,
    ).execute()

    file_id = uploaded["id"]
    web_link = uploaded["webViewLink"]

    # Rendre public
    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
        supportsAllDrives=True,
    ).execute()

    return web_link, file_id
