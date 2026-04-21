from odoo import models, fields

class CasaProvider(models.Model):
    _name = 'casa_hanane.provider'
    _description = 'Fournisseurs Casa (Hanane)'

    name = fields.Char(string='Nom', required=True)
