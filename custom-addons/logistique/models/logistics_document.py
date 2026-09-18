from odoo import models, fields, api


class LogistiqueDoc(models.Model):
    _name = 'logistique.doc'
    _description = 'Document Logistique (Drive)'
    _rec_name = 'document_type'

    entry_id = fields.Many2one(
        'logistique.entry',
        string='Dossier / Entrée',
        required=True,
        ondelete='cascade',
    )
    dossier_id = fields.Many2one(
        'logistique.dossier',
        string='Dossier BL',
        related='entry_id.dossier_id',
        store=True,
        readonly=True,
    )

    document_type = fields.Selection([
        ('other', 'Autre'),
        ('engagement', 'Engagement'),
        ('company_invoice', 'Factures companies'),
    ], string='Type de document', required=True)

    drive_link = fields.Char(
        string='Lien Drive',
        required=False,
        help="Collez le lien Google Drive du document",
    )

    drive_url = fields.Char(
        string='Ouvrir',
        compute='_compute_drive_url',
    )

    file = fields.Binary(string='Fichier (PDF)', attachment=True)
    file_name = fields.Char(string='Nom du fichier')
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
