from odoo import models, fields, api

class LogistiqueDossierCheque(models.Model):
    _name = 'logistique.dossier.cheque'
    _description = 'Chèque Dossier Logistique'

    dossier_id = fields.Many2one('logistique.dossier', string='Dossier', required=True, ondelete='cascade')
    cheque_serie = fields.Char(string='Série Chèque', required=True, size=7)
    date = fields.Date(string='Date')
    beneficiary_id = fields.Many2one('logistique.shipping', string='Bénéficiaire')
    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Devise', required=True, default=lambda self: self.env.ref('base.MAD'))
    ste_id = fields.Many2one('logistique.ste', string='Société', required=True)
    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('fret', 'FRET'),
        ('surestarie', 'Surestarie'),
    ], string='Type')
