import logging
import os
import datetime
import io
import datetime
import io
import os
import tempfile
import base64
import threading
import odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.service import db
import google.auth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import requests

_logger = logging.getLogger(__name__)

class DbBackupDriveConfig(models.Model):
    _name = 'db.backup.drive.config'
    _description = 'Google Drive Backup Configuration'

    name = fields.Char(string="Name", default="Google Drive Backup Config", readonly=True)
    folder_id = fields.Char(string="Google Drive Folder ID", required=True, default="1cmkn6Ev66h3POgimDZuftPnnNn8BDgwR")
    master_password = fields.Char(string="Odoo Master Password", help="Required to perform database dumps.")
    retention_count = fields.Integer(string="Keep Last X Backups", default=7, help="Number of backups to keep in Google Drive. Set to 0 to keep all.")
    
    # OAuth2 Fields
    client_id = fields.Char(string="Client ID")
    client_secret = fields.Char(string="Client Secret")
    refresh_token = fields.Char(string="Refresh Token")
    auth_url = fields.Text(string="Authorization URL", readonly=True)
    auth_code = fields.Char(string="Authorization Code", help="Paste the code received after authorizing.")

    last_backup_date = fields.Datetime(string="Last Backup Date", readonly=True)
    last_backup_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string="Last Backup Status", readonly=True)
    error_message = fields.Text(string="Error Message", readonly=True)

    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'Google Drive Backup Config'})
        return config

    def action_generate_auth_url(self):
        """Generate the URL for the user to authorize."""
        self.ensure_one()
        if not self.client_id or not self.client_secret:
            raise UserError("Please enter Client ID and Client Secret first.")
        
        scopes = ['https://www.googleapis.com/auth/drive.file']
        flow = InstalledAppFlow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=scopes
        )
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        self.auth_url = auth_url

    def action_validate_auth_code(self):
        """Exchange the auth code for a refresh token."""
        self.ensure_one()
        if not self.auth_code:
            raise UserError("Please enter the Authorization Code.")
            
        data = {
            'code': self.auth_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'authorization_code'
        }
        response = requests.post('https://oauth2.googleapis.com/token', data=data).json()
        
        if 'refresh_token' in response:
            self.refresh_token = response['refresh_token']
            self.auth_code = False
            self.auth_url = False
        else:
            raise UserError(f"Error getting refresh token: {response.get('error_description', response.get('error', 'Unknown error'))}")

    def action_backup_now(self):
        """Manually trigger the backup."""
        self.ensure_one()
        # Run in a background thread to avoid HTTP timeouts for large DBs
        threaded_backup = threading.Thread(target=self._run_backup_in_new_thread)
        threaded_backup.start()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sauvegarde Démarrée',
                'message': 'Le backup a été lancé en arrière-plan. Cela peut prendre quelques minutes. Veuillez rafraîchir la page plus tard pour voir le statut.',
                'sticky': False,
                'type': 'info',
            }
        }

    def _run_backup_in_new_thread(self):
        db_name = self.env.cr.dbname
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            config = self.with_env(env)
            # Need to re-fetch the record in the new environment
            config = config.browse(self.id)
            try:
                config._perform_backup()
                cr.commit()
            except Exception as e:
                # Commit the error state so the user can see it in the UI!
                cr.commit()
                _logger.exception("Background backup failed: " + str(e))

    @api.model
    def _run_scheduled_backup(self):
        """Called by Cron."""
        config = self.get_config()
        if config.refresh_token:
            if config.last_backup_status == 'success' and config.last_backup_date:
                if config.last_backup_date.date() == datetime.datetime.utcnow().date():
                    _logger.info("Backup already performed today. Skipping to prevent duplicates from missed cron executions.")
                    return
            config._perform_backup()

    def _perform_backup(self):
        self.ensure_one()
        if not self.refresh_token:
            msg = "Missing Refresh Token. Please authorize the app first."
            self.write({'last_backup_status': 'failed', 'error_message': msg})
            return

        db_name = self.env.cr.dbname
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{db_name}_{timestamp}.zip"
        
        try:
            _logger.info(f"Starting backup for database {db_name} to Google Drive folder {self.folder_id}")
            
            # 1. Dump database to a temporary file to avoid RAM exhaustion and closed file errors
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'wb') as f:
                    db.dump_db(db_name, f, backup_format='zip')
                
                # 2. Authenticate with Google OAuth2
                creds = Credentials(
                    None,
                    refresh_token=self.refresh_token,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    token_uri="https://oauth2.googleapis.com/token"
                )
                service = build('drive', 'v3', credentials=creds)
                
                # 3. Upload to Google Drive
                file_metadata = {
                    'name': filename,
                    'parents': [self.folder_id]
                }
                
                with open(temp_file_path, 'rb') as f:
                    media = MediaIoBaseUpload(f, mimetype='application/zip', resumable=True)
                    
                    file = service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id'
                    ).execute()
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
            _logger.info(f"Backup uploaded successfully to Google Drive. File ID: {file.get('id')}")
            
            # Clean up old backups if retention_count is set
            if self.retention_count > 0:
                try:
                    query = f"'{self.folder_id}' in parents and trashed=false"
                    results = service.files().list(q=query, orderBy="createdTime desc", fields="files(id, name)").execute()
                    files = results.get('files', [])
                    
                    if len(files) > self.retention_count:
                        files_to_delete = files[self.retention_count:]
                        for f in files_to_delete:
                            service.files().delete(fileId=f['id']).execute()
                            _logger.info(f"Deleted old backup: {f.get('name')}")
                except Exception as e:
                    _logger.warning(f"Failed to clean up old backups: {str(e)}")
            
            self.write({
                'last_backup_date': fields.Datetime.now(),
                'last_backup_status': 'success',
                'error_message': False
            })
            
        except Exception as e:
            msg = f"Backup failed: {str(e)}"
            _logger.exception(msg)
            self.write({
                'last_backup_status': 'failed',
                'error_message': msg
            })
            raise UserError(msg)
