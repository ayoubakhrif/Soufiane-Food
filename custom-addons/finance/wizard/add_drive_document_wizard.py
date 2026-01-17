# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AddDriveDocumentWizard(models.TransientModel):
    _name = 'finance.add.drive.document.wizard'
    _description = 'Wizard to add Google Drive document to cheque'

    cheque_id = fields.Many2one(
        'datacheque',
        string='Chèque',
        required=True,
        readonly=True
    )

    doc_type = fields.Selection([
        ('copie_chq', 'Copie du chèque'),
        ('documentation', 'Documentation'),
    ], string='Type de document', required=True)

    def action_open_picker(self):
        """Return action to open the Google Drive Picker template"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'finance_drive_picker',
            'context': {
                'wizard_id': self.id,
                'cheque_id': self.cheque_id.id,
                'doc_type': self.doc_type,
            }
        }

    def action_create_document(self, drive_file_id, file_name, drive_url):
        """Create document record after file selection from picker"""
        self.ensure_one()
        
        # Create the document
        self.env['datacheque.document'].create({
            'cheque_id': self.cheque_id.id,
            'doc_type': self.doc_type,
            'drive_file_id': drive_file_id,
            'file_name': file_name,
            'drive_url': drive_url,
        })
        
        return {'type': 'ir.actions.act_window_close'}
