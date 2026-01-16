from odoo import models, fields

class TransportClient(models.Model):
    _name = 'transport.client'
    _description = 'Clients Transport'

    name = fields.Char(string='Nom', required=True)
