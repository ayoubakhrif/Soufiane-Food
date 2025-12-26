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


def get_drive_service(auth_dir=None, port=8081):
    """Authentifie et retourne un service Google Drive."""
    auth_dir = auth_dir or DEFAULT_AUTH_DIR
    credentials_path = os.path.join(auth_dir, 'credentials.json')
    token_path = os.path.join(auth_dir, 'token.json')

    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path,
                SCOPES,
                redirect_uri=f'http://localhost:{port}'
            )
            creds = flow.run_local_server(port=port, redirect_uri_trailing_slash=False)

        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())

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
