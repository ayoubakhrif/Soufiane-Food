import sys
sys.path.insert(0, r'C:\Program Files\Python310\Lib\site-packages')

import os
import mimetypes
#from google.auth.transport.requests import Request
#from google.oauth2.credentials import Credentials
#from google_auth_oauthlib.flow import InstalledAppFlow
#from googleapiclient.discovery import build
#from googleapiclient.http import MediaFileUpload

# ------------------------------------------------------------
# ⚙️ Configuration
# ------------------------------------------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Répertoire par défaut où sont stockés les credentials
DEFAULT_AUTH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # /cal3iya
    'static', 'drive_auth'
)

# ID du dossier racine "Bon" (fourni par toi)
ROOT_FOLDER_ID = "1YVjJOOPHsVwW7TeE6oxQFSna9bEOylXa"


# ------------------------------------------------------------
# 🔐 Authentification
# ------------------------------------------------------------
def get_drive_servicev2(auth_dir=None):
    """Authentifie l'utilisateur et retourne un service Google Drive (server-compatible)."""
    auth_dir = auth_dir or DEFAULT_AUTH_DIR
    token_path = os.path.join(auth_dir, 'token.json')

    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Token file not found at {token_path}. "
            "Please authenticate first."
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
        raise Exception("Invalid credentials. Please re-authenticate.")

    return build('drive', 'v3', credentials=creds)


# ------------------------------------------------------------
# 📁 Gestion des dossiers
# ------------------------------------------------------------
def get_or_create_folderv2(service, parent_id, folder_name):
    """Cherche un dossier dans parent_id avec ce nom, sinon le crée."""
    results = service.files().list(
        q=f"'{parent_id}' in parents and name='{folder_name}' "
          f"and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']

    # Créer le dossier s’il n’existe pas
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder['id']


# ------------------------------------------------------------
# ☁️ Upload de fichiers
# ------------------------------------------------------------
def upload_to_drivev2(file_path, file_name, auth_dir=None, ste_name=None):
    """
    Envoie un fichier vers Google Drive et retourne (lien, id).
    - file_path : chemin local du fichier (PDF)
    - file_name : nom du fichier sur le Drive
    - ste_name  : nom de la société pour le sous-dossier
    """
    auth_dir = auth_dir or DEFAULT_AUTH_DIR
    service = get_drive_servicev2(auth_dir=auth_dir)

    # Trouver/créer le sous-dossier de la société
    parent_folder_id = ROOT_FOLDER_ID
    if ste_name:
        parent_folder_id = get_or_create_folderv2(service, ROOT_FOLDER_ID, ste_name)

    # Type MIME
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or 'application/pdf'

    # Métadonnées du fichier
    file_metadata = {'name': file_name, 'parents': [parent_folder_id]}

    media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)

    # Upload
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    file_id = uploaded.get('id')
    web_link = uploaded.get('webViewLink')

    # Rendre le fichier accessible via lien public
    service.permissions().create(
        fileId=file_id,
        body={'role': 'reader', 'type': 'anyone'}
    ).execute()

    return web_link, file_id


# ------------------------------------------------------------
# 🧪 Test manuel (utile hors Odoo)
# ------------------------------------------------------------
if __name__ == '__main__':
    base_dir = DEFAULT_AUTH_DIR
    test_file = os.path.join(base_dir, 'test.pdf')

    if os.path.exists(test_file):
        print("📤 Envoi du fichier sur Google Drive...")
        link, file_id = upload_to_drivev2(test_file, 'Bon_Test.pdf', auth_dir=base_dir, ste_name='STE_Test')
        print("✅ Lien public :", link)
        print("🆔 ID du fichier :", file_id)
    else:
        print("⚠️ Aucun fichier test.pdf trouvé dans le dossier.")
