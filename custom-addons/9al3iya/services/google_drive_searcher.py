import sys
sys.path.insert(0, r'C:\Program Files\Python310\Lib\site-packages')

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Utilise la même configuration que google_drive_uploader
SCOPES = ['https://www.googleapis.com/auth/drive.file']
DEFAULT_AUTH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'static', 'drive_auth'
)

# Dossier où chercher les DUM
DUM_FOLDER_ID = "1i9kzO4Pk7X2hFJG2hyh828Sq5uAbarIA"


def get_drive_service(auth_dir=None):
    """Authentifie et retourne un service Google Drive (server-compatible)."""
    auth_dir = auth_dir or DEFAULT_AUTH_DIR
    token_path = os.path.join(auth_dir, 'token.json')

    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Token file not found at {token_path}. "
            "Please authenticate using the upload flow first."
        )

    # Load credentials from existing token
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh if expired (this works on server)
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
        except Exception as e:
            raise Exception(f"Failed to refresh token: {str(e)}")

    if not creds or not creds.valid:
        raise Exception(
            "Invalid credentials. Please re-authenticate using the upload flow."
        )

    return build('drive', 'v3', credentials=creds)


def search_dum_pdf(dum_value, auth_dir=None):
    """
    Cherche un PDF dans le dossier DUM dont le nom contient dum_value.
    Retourne le webViewLink du plus récent en cas de multiples résultats.
    """
    if not dum_value:
        raise ValueError("DUM value cannot be empty")

    service = get_drive_service(auth_dir=auth_dir)

    # Recherche: PDF dans le dossier DUM_FOLDER_ID, nom contient dum_value
    query = (
        f"'{DUM_FOLDER_ID}' in parents "
        f"and name contains '{dum_value}' "
        f"and mimeType='application/pdf' "
        f"and trashed=false"
    )

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, webViewLink, modifiedTime)',
        orderBy='modifiedTime desc'  # Plus récent en premier
    ).execute()

    files = results.get('files', [])

    if not files:
        raise FileNotFoundError(f"Aucun PDF trouvé pour DUM: {dum_value}")

    # Retourne le plus récent
    most_recent = files[0]
    return most_recent.get('webViewLink')
