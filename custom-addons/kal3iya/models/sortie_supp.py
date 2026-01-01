from odoo import models, fields, api

class Kal3iyaSortieSupp(models.Model):
    _name = 'kal3iya.sortie.supp'
    _description = 'Sorties Supplémentaires'
    _order = 'date desc, id desc'

    client_id = fields.Many2one('kal3iya.client', string='Client', required=True, ondelete='cascade')
    amount = fields.Float(string='Montant', required=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    comment = fields.Char(string='Commentaire')
