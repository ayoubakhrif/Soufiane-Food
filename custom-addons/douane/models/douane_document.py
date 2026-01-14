import base64
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DouaneDocument(models.Model):
    _name = 'douane.document'
    _description = 'Document Douane'

    entry_id = fields.Many2one('logistique.entry', string='Dossier', required=True, ondelete='cascade')
    
    type = fields.Selection([
        ('onssa', 'ONSSA'),
        ('invoice_prelevement', 'Facture prélévement'),
        ('analyse', 'Analyse'),
        ('bs', 'Bulletin de sortie'),
        ('dum', 'DUM'),
        ('estimation', 'Estimation'),
    ], string='Type de document', required=True)
    
    file = fields.Binary(string='Fichier', required=True, attachment=True)
    file_name = fields.Char(string='Nom du fichier')
    note = fields.Char(string='Note')

    @api.constrains('file')
    def _check_file_size(self):
        """Limit file size to 5MB"""
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
        for rec in self:
            if rec.file:
                # Binary field is stored as base64, decode to get actual size
                file_size = len(base64.b64decode(rec.file))
                if file_size > MAX_FILE_SIZE:
                    raise ValidationError(
                        f"La taille du fichier ({file_size / (1024*1024):.2f} MB) dépasse la limite autorisée de 5 MB."
                    )
