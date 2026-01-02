from odoo import models, fields

class CasaSaleSupp(models.Model):
    _name = 'casa.sale.supp'
    _description = 'Sortie Supplémentaire'
    _order = 'date desc'

    client_id = fields.Many2one('casa.client', string='Client', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    note = fields.Char(string='Note')
    ste_id = fields.Many2one('casa.ste', string='Société')
