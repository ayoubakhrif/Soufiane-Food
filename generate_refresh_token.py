"""
Script pour générer un Refresh Token Google.
Lancez avec: python generate_refresh_token.py
"""
from google_auth_oauthlib.flow import InstalledAppFlow
import json

# ================== CONFIGURATION ==================
# Collez ici votre Client ID et Client Secret
CLIENT_ID = "VOTRE_CLIENT_ID_ICI"
CLIENT_SECRET = "VOTRE_CLIENT_SECRET_ICI"
# ====================================================

SCOPES = ['https://www.googleapis.com/auth/drive.file']

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
creds = flow.run_local_server(port=0)

print("\n" + "="*60)
print("✅ REFRESH TOKEN GÉNÉRÉ AVEC SUCCÈS !")
print("="*60)
print(f"\nRefresh Token:\n{creds.refresh_token}")
print("\nCopiez ce token et collez-le dans le champ 'Refresh Token' dans Odoo.")
print("="*60)
