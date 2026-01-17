# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class DrivePickerController(http.Controller):

    @http.route('/finance/drive/config', type='json', auth='user')
    def get_drive_config(self):
        """Return Google Drive Picker configuration from settings"""
        icp = request.env['ir.config_parameter'].sudo()
        
        config = {
            'api_key': icp.get_param('finance.google_drive_api_key', ''),
            'client_id': icp.get_param('finance.google_oauth_client_id', ''),
            'app_id': icp.get_param('finance.google_app_id', ''),
            'folder_id': icp.get_param('finance.google_drive_folder_id', ''),
        }
        
        # Check if configuration is complete (folder_id is optional but recommended)
        if not all([config['api_key'], config['client_id'], config['app_id']]):
            return {
                'error': True,
                'message': 'Google Drive configuration incomplete. Please contact administrator.'
            }
        
        return {
            'error': False,
            'config': config
        }

    @http.route('/finance/drive/document/create', type='json', auth='user')
    def create_drive_document(self, wizard_id, drive_file_id, file_name, drive_url):
        """Create a datacheque.document record from Drive picker selection"""
        try:
            wizard = request.env['finance.add.drive.document.wizard'].browse(wizard_id)
            
            if not wizard.exists():
                return {'error': True, 'message': 'Wizard not found'}
            
            # Validate required fields
            if not all([drive_file_id, file_name, drive_url]):
                return {'error': True, 'message': 'Missing required fields'}
            
            # Create document via wizard method
            wizard.action_create_document(drive_file_id, file_name, drive_url)
            
            return {
                'error': False,
                'message': f'Document "{file_name}" ajouté avec succès!'
            }
            
        except Exception as e:
            _logger.error(f"Error creating Drive document: {str(e)}")
            return {
                'error': True,
                'message': f'Error: {str(e)}'
            }
