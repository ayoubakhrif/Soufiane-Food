from odoo import models, fields

class CasaProvider(models.Model):
    _name = 'casa.provider'
    _description = 'Fournisseurs Casa'

    name = fields.Char(string='Nom', required=True)
