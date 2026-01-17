from odoo import models, fields, api

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
        ('copy_chq', 'Copie du chèque'),
        ('payment_doc', 'Documentation'),
        # ➕ plus tard tu ajoutes ici sans toucher aux vues
    ], string='Type de document', required=True)

    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Fichier',
        required=True
    )

    uploaded_by = fields.Many2one(
        'res.users',
        string='Ajouté par',
        default=lambda self: self.env.user,
        readonly=True
    )

    upload_date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        readonly=True
    )
