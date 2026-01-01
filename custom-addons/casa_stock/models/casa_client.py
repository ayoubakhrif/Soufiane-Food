from odoo import models, fields

class CasaClient(models.Model):
    _name = 'casa.client'
    _description = 'Clients Casa'

    name = fields.Char(string='Nom', required=True)
