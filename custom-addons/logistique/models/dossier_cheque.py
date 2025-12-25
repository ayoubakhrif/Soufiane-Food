from odoo import models, fields, api

class LogistiqueDossierCheque(models.Model):
    _name = 'logistique.dossier.cheque'
    _description = 'Chèque Dossier Logistique'

    dossier_id = fields.Many2one('logistique.dossier', string='Dossier', required=True, ondelete='cascade')
    cheque_serie = fields.Char(string='Série Chèque', required=True)
    date = fields.Date(string='Date')
    beneficiary_id = fields.Many2one('logistique.shipping', string='Bénéficiaire')
    amount = fields.Monetary(string='Montant', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Devise', required=True, default=lambda self: self.env.company.currency_id)
    ste_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    type = fields.Selection([
        ('thc', 'THC'),
        ('magasinage', 'Magasinage'),
        ('fret', 'FRET'),
        ('surestarie', 'Surestarie'),
    ], string='Type')
