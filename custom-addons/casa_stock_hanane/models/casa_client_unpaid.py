from odoo import models, fields, api

class CasaClientUnpaid(models.Model):
    _name = 'casa_hanane.client.unpaid'
    _description = 'Impayés Client Casa (Hanane)'
    _order = 'date desc, id desc'

    client_id = fields.Many2one('casa_hanane.client', string='Client', required=True, ondelete='cascade')
    amount = fields.Float(string='Montant', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    comment = fields.Char(string='Commentaire')
