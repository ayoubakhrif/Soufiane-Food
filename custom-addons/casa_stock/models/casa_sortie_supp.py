from odoo import models, fields, api

class CasaSortieSupp(models.Model):
    _name = 'casa.sortie.supp'
    _description = 'Sorties Supplémentaires Casa'
    _order = 'date desc, id desc'

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    amount = fields.Float(string='Montant', required=True)
    comment = fields.Text(string='Commentaire')
    client_id = fields.Many2one('casa.client', string='Client', required=True, ondelete='cascade')
