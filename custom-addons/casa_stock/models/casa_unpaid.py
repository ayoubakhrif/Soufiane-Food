from odoo import models, fields

class CasaUnpaid(models.Model):
    _name = 'casa.unpaid'
    _description = 'Impayé Client'
    _order = 'date desc'

    client_id = fields.Many2one('casa.client', string='Client', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    note = fields.Char(string='Note')
    ste_id = fields.Many2one('casa.ste', string='Société')
