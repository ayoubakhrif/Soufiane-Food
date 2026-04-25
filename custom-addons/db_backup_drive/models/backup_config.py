import logging
import os
import datetime
import io
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.service import db
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

_logger = logging.getLogger(__name__)

class DbBackupDriveConfig(models.Model):
    _name = 'db.backup.drive.config'
    _description = 'Google Drive Backup Configuration'

    name = fields.Char(string="Name", default="Google Drive Backup Config", readonly=True)
    folder_id = fields.Char(string="Google Drive Folder ID", required=True, default="1cmkn6Ev66h3POgimDZuftPnnNn8BDgwR")
    master_password = fields.Char(string="Odoo Master Password", help="Required to perform database dumps.")
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

    def action_backup_now(self):
        """Manually trigger the backup."""
        self.ensure_one()
        self._perform_backup()

    @api.model
    def _run_scheduled_backup(self):
        """Called by Cron."""
        config = self.get_config()
        if config.folder_id:
            config._perform_backup()

    def _perform_backup(self):
        self.ensure_one()
        db_name = self.env.cr.dbname
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{db_name}_{timestamp}.zip"
        
        # Path to service account - adjusted for Docker environment
        # Expected path in Docker: /mnt/extra-addons/google_credentials/service_account.json
        # Check environment variable first, then standard paths
        possible_paths = [
            os.environ.get('GOOGLE_SERVICE_ACCOUNT_PATH', '/mnt/extra-addons/google_credentials/service_account.json'),
            '/mnt/extra-addons/google_credentials/service_account.json',
            'c:\\odoo-repos\\Soufiane-Food\\google_credentials\\service_account.json',
        ]
        
        service_account_path = False
        for path in possible_paths:
            if os.path.exists(path):
                service_account_path = path
                break
        
        if not service_account_path:
            msg = f"Service account file not found. Checked: {', '.join(possible_paths)}"
            self.write({
                'last_backup_status': 'failed',
                'error_message': msg
            })
            _logger.error(msg)
            return

        try:
            _logger.info(f"Starting backup for database {db_name} to Google Drive folder {self.folder_id}")
            
            # 1. Dump database
            # We use 'zip' format to include the filestore
            # Note: odoo.service.db.dump_db returns content via the stream
            buffer = io.BytesIO()
            db.dump_db(db_name, buffer, backup_format='zip')
            buffer.seek(0)
            
            # 2. Authenticate with Google
            scopes = ['https://www.googleapis.com/auth/drive.file']
            creds = service_account.Credentials.from_service_account_file(service_account_path, scopes=scopes)
            service = build('drive', 'v3', credentials=creds)
            
            # 3. Upload to Google Drive
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            media = MediaIoBaseUpload(buffer, mimetype='application/zip', resumable=True)
            
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            _logger.info(f"Backup uploaded successfully to Google Drive. File ID: {file.get('id')}")
            
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
