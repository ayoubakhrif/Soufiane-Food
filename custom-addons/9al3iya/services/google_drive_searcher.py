import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Lecture seule suffisante
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Folder Drive où chercher les PDFs DUM
DUM_FOLDER_ID = "1i9kzO4Pk7X2hFJG2hyh828Sq5uAbarIA"

# Chemin dans le conteneur Docker
SERVICE_ACCOUNT_PATH = "/srv/google_credentials/service_account.json"


def get_drive_service():
    if not os.path.exists(SERVICE_ACCOUNT_PATH):
        raise FileNotFoundError(
            f"Service account file not found at {SERVICE_ACCOUNT_PATH}"
        )

    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH,
        scopes=SCOPES
    )

    return build("drive", "v3", credentials=creds)


def search_dum_pdf(dum_value: str):
    if not dum_value:
        raise ValueError("DUM value cannot be empty")

    service = get_drive_service()

    safe_dum = dum_value.replace("'", "\\'")
    query = (
        f"'{DUM_FOLDER_ID}' in parents and "
        f"mimeType='application/pdf' and "
        f"trashed=false and "
        f"name contains '{safe_dum}'"
    )

    results = service.files().list(
        q=query,
        fields="files(id,name,webViewLink,modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=10,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    files = results.get("files", [])
    if not files:
        raise FileNotFoundError(f"No PDF found for DUM: {dum_value}")

    return files[0]["webViewLink"]
