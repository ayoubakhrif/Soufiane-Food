from odoo import models, fields, api

class TresoreriePaiement(models.Model):
    _name = 'tresorerie.paiement'
    _description = 'Paiement (Trésorerie)'
    _order = 'create_date desc'

    client_id = fields.Many2one('tresorerie.client', string='Client', required=True, ondelete='restrict')
    amount = fields.Float(string='Montant', required=True)
    payment_type = fields.Selection([
        ('especes', 'Espèces'),
        ('cheque', 'Chèques')
    ], string='Type de paiement', required=True, default='especes')
    
    check_date = fields.Date(string='Date du chèque')
    
    date = fields.Date(string='Date du paiement', default=fields.Date.context_today, required=True)
