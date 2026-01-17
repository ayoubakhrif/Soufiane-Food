# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_drive_api_key = fields.Char(
        string='Google Drive API Key',
        config_parameter='finance.google_drive_api_key',
        help='API Key for Google Drive Picker'
    )

    google_oauth_client_id = fields.Char(
        string='Google OAuth Client ID',
        config_parameter='finance.google_oauth_client_id',
        help='OAuth 2.0 Client ID for Google Drive access'
    )

    google_app_id = fields.Char(
        string='Google App ID',
        config_parameter='finance.google_app_id',
        help='Google Cloud Project Number (not Project ID)'
    )
