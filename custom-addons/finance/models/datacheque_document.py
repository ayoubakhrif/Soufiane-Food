from odoo import models, fields, api
from markupsafe import Markup

class DataChequeDocument(models.Model):
    _name = 'datacheque.document'
    _description = 'Documents du chèque'
    _order = 'create_date desc'

    cheque_id = fields.Many2one(
        'datacheque',
        string='Chèque',
        required=True,
        ondelete='cascade'
    )

    doc_type = fields.Selection([
        ('copie_chq', 'Copie du chèque'),
        ('documentation', 'Documentation'),
    ], string='Type de document', required=True)

    # Google Drive fields (no binary storage)
    drive_file_id = fields.Char(
        string='Google Drive File ID',
        required=True,
        help='ID du fichier dans Google Drive'
    )
    
    file_name = fields.Char(
        string='Nom du fichier',
        required=True
    )
    
    drive_url = fields.Char(
        string='Lien Google Drive',
        required=True,
        help='URL de visualisation du fichier'
    )
    
    drive_url_html = fields.Html(
        string='Lien',
        compute='_compute_drive_url_html',
        sanitize=False
    )

    create_uid = fields.Many2one(
        'res.users',
        string='Ajouté par',
        readonly=True
    )

    create_date = fields.Datetime(
        string='Date',
        readonly=True
    )

    @api.depends('drive_url', 'file_name')
    def _compute_drive_url_html(self):
        """Generate clickable link to Google Drive"""
        for rec in self:
            if rec.drive_url and rec.file_name:
                rec.drive_url_html = Markup(
                    f'<a href="{rec.drive_url}" target="_blank" '
                    f'style="color:#007bff;text-decoration:none;">'
                    f'<i class="fa fa-external-link"/> {rec.file_name}'
                    f'</a>'
                )
            else:
                rec.drive_url_html = ''
