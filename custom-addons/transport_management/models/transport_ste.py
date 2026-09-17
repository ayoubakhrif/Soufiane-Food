from odoo import models, fields

class TransportSte(models.Model):
    _name = 'transport.ste'
    _description = 'Societe de Transport'

    name = fields.Char(string='Societe', required=True)
