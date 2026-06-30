from odoo import models, fields, api


class LogistiqueDoc(models.Model):
    _name = 'logistique.doc'
    _description = 'Document Logistique (Drive)'
    _rec_name = 'document_type'

    entry_id = fields.Many2one(
        'logistique.entry',
        string='Dossier',
        required=True,
        ondelete='cascade',
    )

    document_type = fields.Selection([
        ('other', 'Autre'),
        ('engagement', 'Engagement'),
    ], string='Type de document', required=True)

    drive_link = fields.Char(
        string='Lien Drive',
        required=True,
        help="Collez le lien Google Drive du document",
    )

    drive_url = fields.Char(
        string='Ouvrir',
        compute='_compute_drive_url',
    )

    notes = fields.Char(string='Notes')

    @api.depends('drive_link')
    def _compute_drive_url(self):
        for rec in self:
            if rec.drive_link:
                if rec.drive_link.startswith('http'):
                    rec.drive_url = rec.drive_link
                else:
                    rec.drive_url = 'https://' + rec.drive_link
            else:
                rec.drive_url = False
